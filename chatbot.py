import openai
import json
import re
from typing import Dict, List
import os
from dotenv import load_dotenv

load_dotenv()

class TravelChatbot:
    def __init__(self):
        # Khởi tạo OpenAI client
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Template prompt để kiểm tra chủ đề
        self.topic_check_prompt = """
        Bạn là một AI chuyên phân tích chủ đề câu hỏi của người dùng.
        Hãy xác định xem câu hỏi sau có liên quan đến du lịch Việt Nam hay không.

        Câu hỏi: "{user_input}"

        Các chủ đề ĐƯỢC CHẤP NHẬN (liên quan đến du lịch):
        - Hỏi về địa điểm du lịch, thành phố, tỉnh thành Việt Nam
        - Hỏi về thời tiết, khí hậu cho du lịch
        - Hỏi về thời gian du lịch (tháng, mùa)
        - Hỏi về loại địa hình (biển, núi, đồng bằng)
        - Hỏi về vùng miền (Bắc, Trung, Nam)
        - Hỏi về điều kiện thời tiết mong muốn (nhiệt độ, gió, độ ẩm, tầm nhìn)
        - Gợi ý nơi đi chơi, nghỉ dưỡng
        - Lập kế hoạch du lịch

        Các chủ đề KHÔNG ĐƯỢC CHẤP NHẬN (không liên quan đến du lịch):
        - Toán học, vật lý, hóa học
        - Lịch sử, địa lý (không liên quan đến du lịch)
        - Tin học, lập trình, công nghệ
        - Y học, sức khỏe
        - Kinh tế, chính trị, xã hội
        - Giáo dục, học tập
        - Thể thao (không liên quan đến du lịch thể thao)
        - Ẩm thực (trừ khi hỏi về ẩm thực địa phương cho du lịch)
        - Mua sắm (trừ khi hỏi về mua sắm du lịch)
        - Người nổi tiếng, hoặc khi hỏi về danh tính của một nhân vật nào đó
        - Các câu hỏi chung chung không rõ ràng

        Trả về JSON với format:
        {
            "is_travel_related": true/false,
            "confidence": 0.0-1.0,
            "reason": "lý do ngắn gọn"
        }

        Chỉ trả về JSON, không có text khác.
        """

        # Template prompt để trích xuất thông tin
        self.extraction_prompt = """
        Bạn là một AI chuyên phân tích yêu cầu du lịch của người dùng.
        Hãy phân tích câu hỏi sau và trích xuất thông tin về điều kiện thời tiết mong muốn, vùng miền, địa hình, và thời gian.

        Câu hỏi: "{user_input}"

        QUAN TRỌNG: Hãy chú ý đặc biệt đến THÁNG được đề cập trong câu hỏi.

        Hãy trả về kết quả dưới dạng JSON với các trường sau:
        - avgtemp_c: nhiệt độ trung bình mong muốn (°C) - số thực từ 15-35
        - maxwind_kph: tốc độ gió tối đa mong muốn (km/h) - số thực từ 5-30
        - totalprecip_mm: lượng mưa mong muốn (mm) - số thực từ 0-30
        - avghumidity: độ ẩm trung bình mong muốn (%) - số thực từ 50-90
        - cloud_cover_mean: độ che phủ mây mong muốn (%) - số thực từ 0-100
        - month: tháng du lịch (1-12) - PHẢI trích xuất chính xác từ câu hỏi, nếu không có thì null
        - region: vùng miền mong muốn - nếu có đề cập, nếu không thì null
        - terrain: địa hình mong muốn - nếu có đề cập, nếu không thì null
        - preferences: mô tả ngắn gọn về sở thích du lịch

        Quy tắc trích xuất chi tiết:

        THÁNG:
        - "tháng 1" hoặc "tháng một" -> 1
        - "tháng 2" hoặc "tháng hai" -> 2
        - "tháng 3" hoặc "tháng ba" -> 3
        - "tháng 4" hoặc "tháng tư" -> 4
        - "tháng 5" hoặc "tháng năm" -> 5
        - "tháng 6" hoặc "tháng sáu" -> 6
        - "tháng 7" hoặc "tháng bảy" -> 7
        - "tháng 8" hoặc "tháng tám" -> 8
        - "tháng 9" hoặc "tháng chín" -> 9
        - "tháng 10" hoặc "tháng mười" -> 10
        - "tháng 11" hoặc "tháng mười một" -> 11
        - "tháng 12" hoặc "tháng mười hai" -> 12
        - "mùa xuân" -> 2, "mùa hè" -> 6, "mùa thu" -> 9, "mùa đông" -> 12
        - "mùa khô" -> 4, "mùa mưa" -> 8

        NHIỆT ĐỘ (avgtemp_c):
        - "20 độ", "20°C", "20 độ C" -> 20
        - "mát mẻ", "se lạnh" -> 20
        - "nóng", "ấm áp" -> 30
        - "ôn hòa", "dễ chịu" -> 25
        - "lạnh" -> 18

        GIÓ (maxwind_kph):
        - "10 km/h", "10km/h", "10 kmh" -> 10
        - "gió nhẹ", "ít gió" -> 8
        - "gió mạnh" -> 25
        - "không thích gió mạnh" -> 10

        ĐỘ ẨM (avghumidity):
        - "60%", "60 phần trăm" -> 60
        - "khô ráo", "khô" -> 55
        - "ẩm ướt", "ẩm" -> 80
        - "vừa phải" -> 70

        LƯỢNG MƯA (totalprecip_mm):
        - "ít mưa", "khô ráo" -> 10
        - "mưa vừa", "bình thường" -> 20
        - "mưa nhiều", "mùa mưa" -> 30
        - "không mưa" -> 0

        ĐỘ CHE PHỦ MÂY (cloud_cover_mean):
        - "ít mây", "trời quang" -> 20
        - "mây vừa", "bình thường" -> 50
        - "nhiều mây", "u ám" -> 80
        - "trời trong" -> 10

        VÙNG MIỀN (region):
        - "miền Bắc", "Bắc Bộ", "phía Bắc" -> "Trung du và miền núi Bắc Bộ" hoặc "Đồng bằng sông Hồng"
        - "miền Nam", "Nam Bộ", "phía Nam" -> "Đồng bằng sông Cửu Long" hoặc "Đông Nam Bộ"
        - "miền Trung", "Trung Bộ", "phía Trung" -> "Bắc Trung Bộ và Duyên hải miền Trung"
        - "Tây Nguyên", "cao nguyên" -> "Tây Nguyên"
        - "đồng bằng sông Hồng", "Hà Nội", "Hải Phòng" -> "Đồng bằng sông Hồng"
        - "đồng bằng sông Cửu Long", "Mekong", "Cần Thơ", "An Giang", "miền Tây", "phía Tây" -> "Đồng bằng sông Cửu Long"

        ĐỊA HÌNH (terrain):
        - "miền núi", "núi", "vùng núi", "cao", "leo núi" -> "miền núi"
        - "ven biển", "biển", "bãi biển", "tắm biển", "gần biển", "du lịch biển" -> "ven biển"
        - "đồng bằng", "bằng phẳng", "đồng ruộng", "nông thôn", "cánh đồng", "thôn quê" -> "đồng bằng"

        Ví dụ:
        - "Tôi muốn đi chơi vào tháng 11" -> {{"avgtemp_c": 25, "maxwind_kph": 15, "totalprecip_mm": 20, "avghumidity": 70, "cloud_cover_mean": 50, "month": 11, "region": null, "terrain": null, "preferences": "du lịch tháng 11"}}
        - "Tôi muốn nơi mát mẻ 20 độ C vào tháng 12" -> {{"avgtemp_c": 20, "maxwind_kph": 15, "totalprecip_mm": 10, "avghumidity": 70, "cloud_cover_mean": 40, "month": 12, "region": null, "terrain": null, "preferences": "nơi mát mẻ 20°C tháng 12"}}
        - "Du lịch biển miền Trung mùa hè" -> {{"avgtemp_c": 28, "maxwind_kph": 20, "totalprecip_mm": 30, "avghumidity": 75, "cloud_cover_mean": 60, "month": null, "region": "Bắc Trung Bộ và Duyên hải miền Trung", "terrain": "ven biển", "preferences": "du lịch biển miền Trung mùa hè"}}
        - "Tôi thích leo núi ở Tây Nguyên" -> {{"avgtemp_c": 25, "maxwind_kph": 15, "totalprecip_mm": 20, "avghumidity": 70, "cloud_cover_mean": 50, "month": null, "region": "Tây Nguyên", "terrain": "miền núi", "preferences": "leo núi Tây Nguyên"}}
        - "Nơi đồng bằng miền Nam, khô ráo" -> {{"avgtemp_c": 25, "maxwind_kph": 15, "totalprecip_mm": 10, "avghumidity": 55, "cloud_cover_mean": 30, "month": null, "region": "Đồng bằng sông Cửu Long", "terrain": "đồng bằng", "preferences": "đồng bằng miền Nam khô ráo"}}
        - "Tôi muốn đi biển ở miền Bắc" -> {{"avgtemp_c": 25, "maxwind_kph": 15, "totalprecip_mm": 20, "avghumidity": 70, "cloud_cover_mean": 50, "month": null, "region": "Bắc Trung Bộ và Duyên hải miền Trung", "terrain": "ven biển", "preferences": "biển miền Bắc"}}
        - "Nơi nóng 30 độ, ít mưa, trời quang" -> {{"avgtemp_c": 30, "maxwind_kph": 15, "totalprecip_mm": 10, "avghumidity": 60, "cloud_cover_mean": 20, "month": null, "region": null, "terrain": null, "preferences": "nóng 30°C, ít mưa, trời quang"}}

        Chỉ trả về JSON, không có text khác.
        """

    def check_travel_topic(self, user_input: str) -> Dict:
        """
        Kiểm tra xem câu hỏi có liên quan đến du lịch hay không
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": "Bạn là một AI chuyên phân tích chủ đề câu hỏi."},
                    {"role": "user", "content": self.topic_check_prompt.format(user_input=user_input)}
                ],
                temperature=0.1,
                max_tokens=200
            )

            content = response.choices[0].message.content.strip()

            # Trích xuất JSON từ response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                # Làm sạch JSON string
                json_str = re.sub(r'\n\s*', ' ', json_str)  # Loại bỏ newline và whitespace thừa
                json_str = re.sub(r',\s*}', '}', json_str)  # Loại bỏ dấu phay thừa
                try:
                    result = json.loads(json_str)
                    return result
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}, content: {json_str}")
                    return self._check_travel_topic_fallback(user_input)
            else:
                # Fallback: sử dụng regex để kiểm tra
                return self._check_travel_topic_fallback(user_input)

        except Exception as e:
            print(f"Error in check_travel_topic: {e}")
            # Fallback: sử dụng regex để kiểm tra
            return self._check_travel_topic_fallback(user_input)

    def _check_travel_topic_fallback(self, user_input: str) -> Dict:
        """
        Fallback method để kiểm tra chủ đề bằng regex
        Chỉ chấp nhận câu có từ khóa du lịch rõ ràng
        """
        user_input_lower = user_input.lower().strip()

        # Kiểm tra độ dài câu
        word_count = len(user_input_lower.split())

        # Từ khóa liên quan đến du lịch - mở rộng và chi tiết hơn
        travel_keywords = [
            # Từ khóa du lịch chung (cụ thể hơn)
            r'du\s*lịch', r'đi\s*chơi', r'nghỉ\s*dưỡng', r'tham\s*quan', r'tour',
            r'địa\s*điểm\s*du\s*lịch', r'nơi\s*du\s*lịch', r'điểm\s*đến',

            # Địa danh và vùng miền
            r'thành\s*phố', r'tỉnh', r'vùng', r'khu\s*vực',
            r'miền\s*bắc', r'miền\s*trung', r'miền\s*nam', r'tây\s*nguyên',
            r'bắc\s*bộ', r'trung\s*bộ', r'nam\s*bộ',

            # Địa hình và cảnh quan
            r'biển', r'núi', r'đồng\s*bằng', r'ven\s*biển', r'bãi\s*biển',
            r'leo\s*núi', r'tắm\s*biển', r'ngắm\s*cảnh', r'phong\s*cảnh',

            # Thời tiết và khí hậu cho du lịch
            r'thời\s*tiết.*du\s*lịch', r'khí\s*hậu.*du\s*lịch',
            r'thời\s*tiết.*tháng', r'khí\s*hậu.*tháng',
            r'mát\s*mẻ', r'nóng.*du\s*lịch', r'lạnh.*du\s*lịch',
            r'mùa\s*khô', r'mùa\s*mưa', r'mùa\s*xuân', r'mùa\s*hè', r'mùa\s*thu', r'mùa\s*đông',

            # Tên địa danh cụ thể
            r'hà\s*nội', r'sài\s*gòn', r'tp\s*hồ\s*chí\s*minh', r'đà\s*nẵng',
            r'huế', r'nha\s*trang', r'hạ\s*long', r'sapa', r'đà\s*lạt',
            r'phú\s*quốc', r'cần\s*thơ', r'hội\s*an', r'vũng\s*tàu',

            # Hoạt động du lịch
            r'khách\s*sạn', r'resort', r'homestay', r'lưu\s*trú',
            r'ăn\s*uống.*du\s*lịch', r'món\s*ngon.*địa\s*phương', r'đặc\s*sản', r'ẩm\s*thực.*du\s*lịch',
            r'lễ\s*hội', r'văn\s*hóa.*du\s*lịch', r'truyền\s*thống.*du\s*lịch',

            # Từ khóa gợi ý cụ thể về du lịch
            r'gợi\s*ý.*du\s*lịch', r'gợi\s*ý.*địa\s*điểm', r'khuyên.*du\s*lịch',
            r'nên\s*đi.*đâu', r'đi\s*đâu.*du\s*lịch', r'ở\s*đâu.*du\s*lịch',
            r'muốn\s*đi.*biển', r'muốn\s*đi.*núi', r'muốn\s*đi.*du\s*lịch'
        ]

        # Từ khóa ngắn cần có context (chỉ chấp nhận khi có từ khóa khác)
        short_keywords = [
            r'\btháng\b', r'\bmùa\b', r'\bgió\b', r'\bđộ\s*ẩm\b', r'\bnhiệt\s*độ\b',
            r'\bthời\s*tiết\b', r'\bkhí\s*hậu\b'
        ]

        # Kiểm tra có từ khóa du lịch chính không
        has_main_travel_keywords = any(re.search(keyword, user_input_lower) for keyword in travel_keywords)

        # Kiểm tra có từ khóa ngắn không
        has_short_keywords = any(re.search(keyword, user_input_lower) for keyword in short_keywords)

        # Nếu có từ khóa du lịch chính rõ ràng
        if has_main_travel_keywords:
            return {
                "is_travel_related": True,
                "confidence": 0.8,
                "reason": "Chứa từ khóa du lịch rõ ràng"
            }

        # Nếu chỉ có từ khóa ngắn và câu đủ dài (có thể là về du lịch)
        if has_short_keywords and word_count >= 4:
            return {
                "is_travel_related": True,
                "confidence": 0.6,
                "reason": "Có từ khóa liên quan, có thể về du lịch"
            }

        # Nếu câu quá ngắn (dưới 3 từ)
        if word_count < 3:
            return {
                "is_travel_related": False,
                "confidence": 0.9,
                "reason": "Câu quá ngắn, cần nói rõ hơn về du lịch"
            }

        # Nếu câu dài nhưng không có từ khóa du lịch
        return {
            "is_travel_related": False,
            "confidence": 0.7,
            "reason": "Không chứa từ khóa du lịch"
        }

    def generate_polite_refusal(self, user_input: str, topic_result: Dict) -> str:
        """Tạo câu trả lời từ chối lịch sự"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý du lịch Việt Nam. Từ chối lịch sự câu hỏi không liên quan và hướng dẫn về du lịch."},
                    {"role": "user", "content": f"Câu hỏi: '{user_input}' không liên quan du lịch. Hãy từ chối lịch sự và hướng dẫn."}
                ],
                temperature=0.7,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except:
            return self._get_default_refusal(topic_result.get('reason', ''))

    def _get_default_refusal(self, reason: str = "") -> str:
        """Câu trả lời từ chối mặc định"""
        import random

        messages = {
            "quá ngắn": [
                "Bạn có thể nói rõ hơn về yêu cầu du lịch không? Ví dụ: 'Tôi muốn đi biển miền Trung tháng 6'.",
                "Câu hỏi hơi ngắn, hãy cho tôi biết cụ thể về nơi bạn muốn đi, thời gian hoặc thời tiết bạn thích nhé!"
            ],
            "default": [
                "Tôi chỉ hỗ trợ về du lịch Việt Nam. Bạn có thể hỏi về địa điểm, thời tiết, thời gian du lịch phù hợp.",
                "Xin lỗi, tôi chuyên tư vấn du lịch Việt Nam. Bạn muốn tôi gợi ý địa điểm thú vị không?",
                "Tôi chỉ chuyên về du lịch Việt Nam. Hãy cho tôi biết bạn muốn đi đâu, khi nào nhé!"
            ]
        }

        if "quá ngắn" in reason:
            return random.choice(messages["quá ngắn"])
        return random.choice(messages["default"])

    def process_user_input(self, user_input: str) -> tuple:
        """
        Xử lý input của người dùng - kiểm tra chủ đề trước khi xử lý
        Returns: (is_travel_related: bool, response_or_preferences: str or Dict)
        """
        # Kiểm tra chủ đề trước
        topic_result = self.check_travel_topic(user_input)

        # Nếu không liên quan đến du lịch và confidence cao
        if not topic_result.get('is_travel_related', False) and topic_result.get('confidence', 0) > 0.6:
            refusal_response = self.generate_polite_refusal(user_input, topic_result)
            return False, refusal_response

        # Nếu liên quan đến du lịch hoặc không chắc chắn, tiếp tục xử lý
        preferences = self.extract_travel_preferences(user_input)
        return True, preferences

    def extract_travel_preferences(self, user_input: str) -> Dict:
        """
        Sử dụng OpenAI để trích xuất thông tin du lịch từ input của user
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": "Bạn là một AI chuyên phân tích yêu cầu du lịch."},
                    {"role": "user", "content": self.extraction_prompt.format(user_input=user_input)}
                ],
                temperature=0.1,  # Giảm temperature để có kết quả ổn định hơn
                max_tokens=500
            )

            # Trích xuất JSON từ response
            content = response.choices[0].message.content.strip()

            # Tìm JSON trong response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                # Làm sạch JSON string
                json_str = re.sub(r'\n\s*', ' ', json_str)  # Loại bỏ newline và whitespace thừa
                json_str = re.sub(r',\s*}', '}', json_str)  # Loại bỏ dấu phay thừa
                try:
                    preferences = json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"JSON decode error in extract_travel_preferences: {e}")
                    return self._get_default_preferences_with_fallback(user_input)

                # Fallback extractions using unified method
                fallback_map = {
                    'month': ('month', None),
                    'avgtemp_c': ('temperature', (15, 35)),
                    'maxwind_kph': ('wind', (5, 30)),
                    'avghumidity': ('humidity', (50, 90)),
                    'totalprecip_mm': ('precipitation', (0, 30)),
                    'cloud_cover_mean': ('cloud_cover', (0, 100)),
                    'region': ('region', None),
                    'terrain': ('terrain', None)
                }

                for pref_key, (extract_type, valid_range) in fallback_map.items():
                    if preferences.get(pref_key) is None or (valid_range and not (valid_range[0] <= preferences.get(pref_key, 0) <= valid_range[1])):
                        fallback_value = self._extract_fallback(user_input, extract_type)
                        if fallback_value is not None:
                            preferences[pref_key] = fallback_value

                # Validate và set default values
                preferences = self._validate_preferences(preferences)
                return preferences
            else:
                return self._get_default_preferences_with_fallback(user_input)

        except Exception as e:
            print(f"Error in extract_travel_preferences: {e}")
            return self._get_default_preferences_with_fallback(user_input)
    
    def _validate_preferences(self, preferences: Dict) -> Dict:
        """Validate và điều chỉnh các giá trị preferences với thuộc tính mới"""
        validated = {}

        # Validate avgtemp_c (15-35)
        validated['avgtemp_c'] = max(15, min(35, preferences.get('avgtemp_c', 25)))

        # Validate maxwind_kph (5-30)
        validated['maxwind_kph'] = max(5, min(30, preferences.get('maxwind_kph', 15)))

        # Validate totalprecip_mm (0-30) - thuộc tính mới với range cập nhật
        validated['totalprecip_mm'] = max(0, min(30, preferences.get('totalprecip_mm', 10)))

        # Validate avghumidity (50-90)
        validated['avghumidity'] = max(50, min(90, preferences.get('avghumidity', 70)))

        # Validate cloud_cover_mean (0-100) - thuộc tính mới
        validated['cloud_cover_mean'] = max(0, min(100, preferences.get('cloud_cover_mean', 50)))

        # Validate month (1-12 or None)
        month = preferences.get('month')
        if month is not None:
            validated['month'] = max(1, min(12, int(month)))
        else:
            validated['month'] = None

        # Copy region và terrain
        validated['region'] = preferences.get('region')
        validated['terrain'] = preferences.get('terrain')

        validated['preferences'] = preferences.get('preferences', 'du lịch chung')

        return validated
    
    def _extract_fallback(self, user_input: str, extract_type: str):
        """Unified fallback method để trích xuất thông tin bằng regex"""
        user_input_lower = user_input.lower()

        if extract_type == "month":
            month_patterns = {
                12: [r'tháng\s*12\b', r'tháng\s*mười\s*hai\b'],
                11: [r'tháng\s*11\b', r'tháng\s*mười\s*một\b'],
                10: [r'tháng\s*10\b', r'tháng\s*mười\b(?!\s*(một|hai))'],
                1: [r'tháng\s*1\b', r'tháng\s*một\b'], 2: [r'tháng\s*2\b', r'tháng\s*hai\b'],
                3: [r'tháng\s*3\b', r'tháng\s*ba\b'], 4: [r'tháng\s*4\b', r'tháng\s*tư\b'],
                5: [r'tháng\s*5\b', r'tháng\s*năm\b'], 6: [r'tháng\s*6\b', r'tháng\s*sáu\b'],
                7: [r'tháng\s*7\b', r'tháng\s*bảy\b'], 8: [r'tháng\s*8\b', r'tháng\s*tám\b'],
                9: [r'tháng\s*9\b', r'tháng\s*chín\b']
            }
            for month, patterns in month_patterns.items():
                if any(re.search(p, user_input_lower) for p in patterns):
                    return month

        elif extract_type == "temperature":
            # Tìm số + đơn vị
            for pattern in [r'(\d+(?:\.\d+)?)\s*(?:độ|°)\s*c?\b', r'nhiệt\s*độ\s*(\d+(?:\.\d+)?)']:
                match = re.search(pattern, user_input_lower)
                if match:
                    temp = float(match.group(1))
                    if 15 <= temp <= 35: return temp
            # Từ khóa
            if re.search(r'mát\s*mẻ|lạnh', user_input_lower): return 20.0
            if re.search(r'nóng|ấm\s*áp', user_input_lower): return 30.0
            if re.search(r'ôn\s*hòa|dễ\s*chịu', user_input_lower): return 25.0

        elif extract_type == "wind":
            # Tìm số + đơn vị
            for pattern in [r'(\d+(?:\.\d+)?)\s*km/h\b', r'gió\s*(\d+(?:\.\d+)?)']:
                match = re.search(pattern, user_input_lower)
                if match:
                    wind = float(match.group(1))
                    if 5 <= wind <= 30: return wind
            # Từ khóa
            if re.search(r'không\s*thích\s*gió|ít\s*gió', user_input_lower): return 6.0
            if re.search(r'gió\s*nhẹ', user_input_lower): return 8.0
            if re.search(r'gió\s*mạnh', user_input_lower): return 25.0

        elif extract_type == "humidity":
            # Tìm số + đơn vị
            for pattern in [r'(\d+(?:\.\d+)?)\s*%\b', r'độ\s*ẩm\s*(\d+(?:\.\d+)?)']:
                match = re.search(pattern, user_input_lower)
                if match:
                    humidity = float(match.group(1))
                    if 50 <= humidity <= 90: return humidity
            # Từ khóa
            if re.search(r'khô\s*ráo|khô', user_input_lower): return 55.0
            if re.search(r'ẩm\s*ướt|ẩm', user_input_lower): return 80.0
            if re.search(r'vừa\s*phải', user_input_lower): return 70.0

        elif extract_type == "precipitation":
            # Tìm số + đơn vị
            for pattern in [r'(\d+(?:\.\d+)?)\s*mm\b', r'mưa\s*(\d+(?:\.\d+)?)']:
                match = re.search(pattern, user_input_lower)
                if match:
                    precip = float(match.group(1))
                    if 0 <= precip <= 30: return precip
            # Từ khóa
            if re.search(r'không\s*mưa', user_input_lower): return 0.0
            if re.search(r'ít\s*mưa|khô\s*ráo', user_input_lower): return 10.0
            if re.search(r'mưa\s*vừa|bình\s*thường', user_input_lower): return 20.0
            if re.search(r'mưa\s*nhiều|mùa\s*mưa', user_input_lower): return 30.0

        elif extract_type == "cloud_cover":
            # Tìm số + đơn vị
            for pattern in [r'(\d+(?:\.\d+)?)\s*%\s*mây', r'mây\s*(\d+(?:\.\d+)?)']:
                match = re.search(pattern, user_input_lower)
                if match:
                    cloud = float(match.group(1))
                    if 0 <= cloud <= 100: return cloud
            # Từ khóa
            if re.search(r'trời\s*quang|ít\s*mây', user_input_lower): return 20.0
            if re.search(r'nhiều\s*mây|u\s*ám', user_input_lower): return 80.0
            if re.search(r'mây\s*vừa|bình\s*thường', user_input_lower): return 50.0

        elif extract_type == "region":
            regions = {
                "Tây Nguyên": [r'tây\s*nguyên', r'đà\s*lạt'],
                "Đồng bằng sông Hồng": [r'hà\s*nội', r'hải\s*phòng', r'miền\s*bắc'],
                "Đồng bằng sông Cửu Long": [r'cần\s*thơ', r'miền\s*nam', r'miền\s*tây'],
                "Bắc Trung Bộ và Duyên hải miền Trung": [r'miền\s*trung', r'huế', r'đà\s*nẵng', r'nha\s*trang']
            }
            for region, patterns in regions.items():
                if any(re.search(p, user_input_lower) for p in patterns):
                    return region

        elif extract_type == "terrain":
            terrains = {
                "ven biển": [r'biển', r'bãi\s*biển', r'tắm\s*biển'],
                "miền núi": [r'núi', r'leo\s*núi', r'vùng\s*núi'],
                "đồng bằng": [r'đồng\s*bằng', r'nông\s*thôn']
            }
            for terrain, patterns in terrains.items():
                if any(re.search(p, user_input_lower) for p in patterns):
                    return terrain

        return None

    def _has_specific_wind_pattern(self, user_input: str) -> bool:
        """Kiểm tra xem có pattern gió cụ thể không"""
        return bool(re.search(r'(không\s*thích\s*gió|ít\s*gió|gió\s*nhẹ|gió\s*mạnh|\d+\s*km/h)', user_input.lower()))

    def _get_default_preferences(self) -> Dict:
        """Trả về preferences mặc định với thuộc tính mới"""
        return {
            'avgtemp_c': 27,
            'maxwind_kph': 15,
            'totalprecip_mm': 10,
            'avghumidity': 65,
            'cloud_cover_mean': 60, 
            'month': None,
            'region': None,
            'terrain': None,
            'preferences': 'du lịch chung'
        }

    def _get_default_preferences_with_fallback(self, user_input: str) -> Dict:
        """Trả về preferences mặc định với fallback extractions"""
        preferences = self._get_default_preferences()

        # Extract all using unified method
        extractions = {
            'month': self._extract_fallback(user_input, 'month'),
            'avgtemp_c': self._extract_fallback(user_input, 'temperature'),
            'maxwind_kph': self._extract_fallback(user_input, 'wind'),
            'avghumidity': self._extract_fallback(user_input, 'humidity'),
            'totalprecip_mm': self._extract_fallback(user_input, 'precipitation'),
            'cloud_cover_mean': self._extract_fallback(user_input, 'cloud_cover'),
            'region': self._extract_fallback(user_input, 'region'),
            'terrain': self._extract_fallback(user_input, 'terrain')
        }

        # Update preferences with extracted values
        for key, value in extractions.items():
            if value is not None:
                preferences[key] = value

        # Build description
        desc_parts = []
        if extractions['month']: desc_parts.append(f"tháng {extractions['month']}")
        if extractions['avgtemp_c']: desc_parts.append(f"{extractions['avgtemp_c']}°C")
        if extractions['maxwind_kph']: desc_parts.append(f"gió {extractions['maxwind_kph']}km/h")
        if extractions['avghumidity']: desc_parts.append(f"độ ẩm {extractions['avghumidity']}%")
        if extractions['totalprecip_mm'] is not None: desc_parts.append(f"mưa {extractions['totalprecip_mm']}mm")
        if extractions['cloud_cover_mean'] is not None: desc_parts.append(f"mây {extractions['cloud_cover_mean']}%")
        if extractions['region']: desc_parts.append(extractions['region'])
        if extractions['terrain']: desc_parts.append(extractions['terrain'])

        if desc_parts:
            preferences['preferences'] = f'du lịch {", ".join(desc_parts)}'

        return preferences
    
    def generate_response(self, user_input: str, recommendations: List[Dict] = None) -> str:
        """
        Tạo response tự nhiên - có thể là gợi ý du lịch hoặc từ chối lịch sự
        """
        # Kiểm tra chủ đề trước
        is_travel_related, result = self.process_user_input(user_input)

        # Nếu không liên quan đến du lịch, trả về câu từ chối
        if not is_travel_related:
            return result  # result là câu từ chối

        # Nếu liên quan đến du lịch nhưng không có recommendations, tạo response chung
        if recommendations is None or len(recommendations) == 0:
            return "Tôi hiểu yêu cầu của bạn, nhưng hiện tại chưa tìm được địa điểm phù hợp. Bạn có thể cung cấp thêm thông tin cụ thể về thời gian, địa điểm, hoặc điều kiện thời tiết mong muốn không?"

        # Tạo response cho gợi ý du lịch
        try:
            # Tạo context từ recommendations
            locations_text = ""
            for i, rec in enumerate(recommendations[:5], 1):
                locations_text += f"{i}. {rec['city']}, {rec['province']} ({rec['region']}) - Tháng {rec['month']}\n"
                locations_text += f"   Nhiệt độ: {rec['avgtemp_c']:.1f}°C, Gió: {rec['maxwind_kph']:.1f}km/h, "
                locations_text += f"Mưa: {rec['totalprecip_mm']:.1f}mm, Độ ẩm: {rec['avghumidity']:.1f}%, "
                locations_text += f"Mây: {rec['cloud_cover_mean']:.1f}%\n"
                locations_text += f"   Điểm phù hợp: {rec['score']:.2f}\n\n"

            response_prompt = f"""
            Dựa trên yêu cầu du lịch: "{user_input}"

            Tôi đã tìm được những địa điểm phù hợp sau:

            {locations_text}

            Hãy viết một phản hồi tự nhiên, thân thiện để giới thiệu những địa điểm này cho người dùng.
            Phản hồi nên:
            - Bắt đầu bằng lời chào thân thiện
            - Giải thích ngắn gọn tại sao những địa điểm này phù hợp
            - Mô tả đặc điểm thời tiết của từng nơi
            - Kết thúc bằng lời khuyên hoặc câu hỏi để tiếp tục hỗ trợ
            - CHỈ tập trung vào du lịch Việt Nam
            Viết bằng tiếng Việt, tối đa 300 từ.
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": "Bạn là một chuyên gia tư vấn du lịch Việt Nam thân thiện. Chỉ trả lời về du lịch trong nước."},
                    {"role": "user", "content": response_prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Error in generate_response: {e}")
            return self._get_default_response(recommendations)
    
    def _get_default_response(self, recommendations: List[Dict]) -> str:
        """Tạo response mặc định khi OpenAI không khả dụng"""
        if not recommendations:
            return "Xin lỗi, tôi không tìm thấy địa điểm nào phù hợp với yêu cầu của bạn. Bạn có thể thử với điều kiện khác không?"
        
        response = "Dựa trên yêu cầu của bạn, tôi gợi ý những địa điểm sau:\n\n"
        
        for i, rec in enumerate(recommendations[:5], 1):
            response += f"{i}. **{rec['city']}, {rec['province']}** ({rec['region']})\n"
            response += f"   - Thời gian: Tháng {rec['month']}\n"
            response += f"   - Thời tiết: {rec['avgtemp_c']:.1f}°C, gió {rec['maxwind_kph']:.1f}km/h, "
            response += f"mưa {rec['totalprecip_mm']:.1f}mm, độ ẩm {rec['avghumidity']:.1f}%\n"
            response += f"   - Điểm phù hợp: {rec['score']:.2f}\n\n"
        
        response += "Bạn có muốn biết thêm thông tin về địa điểm nào không?"
        return response

    def chat(self, user_input: str, recommendations: List[Dict] = None) -> str:
        """
        Phương thức chính để chat với người dùng
        Tự động kiểm tra chủ đề và trả về phản hồi phù hợp
        """
        return self.generate_response(user_input, recommendations)

# Main entry point for testing
if __name__ == "__main__":
    chatbot = TravelChatbot()
    print("Travel Chatbot initialized successfully!")
