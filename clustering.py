import pandas as pd
import numpy as np
from typing import Dict, List
from sklearn.metrics.pairwise import euclidean_distances
from sklearn.preprocessing import StandardScaler

class TravelRecommendationEngine:
    def __init__(self, data_path: str = "df_ranking.csv"):
        """
        Khởi tạo recommendation engine với dataset mới
        """
        self.df = pd.read_csv(data_path)
        self.scaler = StandardScaler()
        # Cập nhật features với thuộc tính thời tiết mới
        self.features = ['avgtemp_c', 'maxwind_kph', 'totalprecip_mm', 'avghumidity', 'cloud_cover_mean']

        # Chuẩn hóa dữ liệu
        self.df_scaled = self.df.copy()
        self.df_scaled[self.features] = self.scaler.fit_transform(self.df[self.features])

        # Lấy centroids (cập nhật tên cột)
        self.centroids = self.df[self.df['is_centroid'] == True].copy()
        print(f"Loaded {len(self.df)} records with {len(self.centroids)} centroids")
        print(f"Weather features: {self.features}")
    
    def find_best_cluster(self, preferences: Dict) -> int:
        """
        Tìm cluster có centroid gần nhất với preferences của user
        """
        # Tạo vector từ preferences với thuộc tính mới
        user_data = pd.DataFrame({
            'avgtemp_c': [preferences['avgtemp_c']],
            'maxwind_kph': [preferences['maxwind_kph']],
            'totalprecip_mm': [preferences.get('totalprecip_mm', 20.0)],  # Default precipitation
            'avghumidity': [preferences['avghumidity']],
            'cloud_cover_mean': [preferences.get('cloud_cover_mean', 50.0)]  # Default cloud cover
        })

        # Chuẩn hóa user vector
        user_vector_scaled = self.scaler.transform(user_data)

        # Tính khoảng cách đến các centroids
        centroid_features = self.centroids[self.features].values
        centroid_features_scaled = self.scaler.transform(centroid_features)

        distances = euclidean_distances(user_vector_scaled, centroid_features_scaled)[0]

        # Tìm centroid gần nhất
        closest_centroid_idx = np.argmin(distances)
        best_cluster = self.centroids.iloc[closest_centroid_idx]['cluster']

        return int(best_cluster)

    def _row_to_dict(self, row) -> Dict:
        """Convert DataFrame row to recommendation dict"""
        return {
            'city': row['name'], 'province': row['province'], 'region': row['region'],
            'terrain': row['terrain'], 'lat': row['lat'], 'lon': row['lon'],
            'month': int(row['month']), 'avgtemp_c': float(row['avgtemp_c']),
            'maxwind_kph': float(row['maxwind_kph']), 'totalprecip_mm': float(row['totalprecip_mm']),
            'avghumidity': float(row['avghumidity']), 'cloud_cover_mean': float(row['cloud_cover_mean']),
            'score': float(row['hci']), 'cluster': int(row['cluster'])
        }

    def get_recommendations(self, preferences: Dict, top_k: int = 5) -> List[Dict]:
        """
        Lấy top K recommendations dựa trên preferences
        """
        # Bắt đầu với toàn bộ dữ liệu
        filtered_data = self.df.copy()

        # Lọc theo tháng nếu có
        if preferences.get('month') is not None:
            month_data = filtered_data[filtered_data['month'] == preferences['month']]
            if len(month_data) > 0:
                filtered_data = month_data

        # Lọc theo region nếu có
        if preferences.get('region') is not None:
            region_data = filtered_data[filtered_data['region'] == preferences['region']]
            if len(region_data) > 0:
                filtered_data = region_data

        # Lọc theo terrain nếu có
        if preferences.get('terrain') is not None:
            terrain_data = filtered_data[filtered_data['terrain'] == preferences['terrain']]
            if len(terrain_data) > 0:
                filtered_data = terrain_data

        # Nếu sau khi lọc không còn dữ liệu, fallback về cluster
        if len(filtered_data) == 0:
            best_cluster = self.find_best_cluster(preferences)
            filtered_data = self.df[self.df['cluster'] == best_cluster].copy()
        else:
            # Nếu còn dữ liệu, tìm cluster tốt nhất trong dữ liệu đã lọc
            if len(filtered_data) > top_k * 2:  # Chỉ dùng cluster nếu có đủ dữ liệu
                best_cluster = self.find_best_cluster(preferences)
                cluster_data = filtered_data[filtered_data['cluster'] == best_cluster]
                if len(cluster_data) > 0:
                    filtered_data = cluster_data

        # Sắp xếp theo hci (chỉ số du lịch) giảm dần thay vì score
        filtered_data = filtered_data.sort_values('hci', ascending=False)

        # Lấy top K
        recommendations = filtered_data.head(top_k)

        return [self._row_to_dict(row) for _, row in recommendations.iterrows()]
    
    def get_cluster_info(self, cluster_id: int) -> Dict:
        """
        Lấy thông tin về một cluster với thuộc tính mới
        """
        cluster_data = self.df[self.df['cluster'] == cluster_id]
        centroid = self.centroids[self.centroids['cluster'] == cluster_id]

        if len(cluster_data) == 0:
            return {}

        return {
            'cluster_id': int(cluster_id),
            'total_locations': int(len(cluster_data)),
            'avg_temp': float(cluster_data['avgtemp_c'].mean()),
            'avg_wind': float(cluster_data['maxwind_kph'].mean()),
            'avg_precipitation': float(cluster_data['totalprecip_mm'].mean()),
            'avg_humidity': float(cluster_data['avghumidity'].mean()),
            'avg_cloud_cover': float(cluster_data['cloud_cover_mean'].mean()),
            'avg_hci': float(cluster_data['hci'].mean()),  # Chỉ số du lịch
            'centroid_location': {
                'city': str(centroid.iloc[0]['name']) if len(centroid) > 0 else 'Unknown',
                'province': str(centroid.iloc[0]['province']) if len(centroid) > 0 else 'Unknown'
            } if len(centroid) > 0 else {}
        }
    
    def search_by_location(self, location_name: str, top_k: int = 5) -> List[Dict]:
        """
        Tìm kiếm theo tên địa điểm với dataset mới
        """
        # Tìm kiếm không phân biệt hoa thường
        location_name = location_name.lower()

        # Tìm trong name và province
        mask = (
            self.df['name'].str.lower().str.contains(location_name, na=False) |
            self.df['province'].str.lower().str.contains(location_name, na=False)
        )

        # Sắp xếp theo hci
        results = self.df[mask].sort_values('hci', ascending=False).head(top_k)

        return [self._row_to_dict(row) for _, row in results.iterrows()]
    
    def get_all_clusters_summary(self) -> List[Dict]:
        """
        Lấy tóm tắt về tất cả các clusters
        """
        clusters = []
        for cluster_id in sorted(self.df['cluster'].unique()):
            info = self.get_cluster_info(cluster_id)
            if info:
                clusters.append(info)
        return clusters
