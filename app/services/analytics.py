# Service d'analytics respectueux de la vie privée
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.database import get_db_connection
import logging

logger = logging.getLogger(__name__)

class PrivacyFriendlyAnalytics:
    """
    Analytics respectueux de la vie privée basé sur les données déjà collectées
    et des métriques anonymisées côté serveur.
    """
    
    @staticmethod
    def get_sales_analytics():
        """Statistiques de vente basées sur les commandes"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Ventes par jour (30 derniers jours)
            cursor.execute("""
                SELECT DATE(created_at) as date, 
                       COUNT(*) as orders_count,
                       SUM(total) as daily_revenue
                FROM orders 
                WHERE created_at >= DATE('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """)
            daily_sales = cursor.fetchall()
            
            # Œuvres les plus vendues
            cursor.execute("""
                SELECT a.title, COUNT(oi.artwork_id) as sales_count
                FROM order_items oi
                JOIN artworks a ON oi.artwork_id = a.id
                JOIN orders o ON oi.order_id = o.id
                WHERE o.created_at >= DATE('now', '-90 days')
                GROUP BY oi.artwork_id, a.title
                ORDER BY sales_count DESC
                LIMIT 10
            """)
            popular_artworks = cursor.fetchall()
            
            # Tendances mensuelles
            cursor.execute("""
                SELECT strftime('%Y-%m', created_at) as month,
                       COUNT(*) as orders,
                       SUM(total) as revenue,
                       AVG(total) as avg_order_value
                FROM orders
                WHERE created_at >= DATE('now', '-12 months')
                GROUP BY strftime('%Y-%m', created_at)
                ORDER BY month DESC
            """)
            monthly_trends = cursor.fetchall()
            
            return {
                "daily_sales": [dict(row) for row in daily_sales],
                "popular_artworks": [dict(row) for row in popular_artworks],
                "monthly_trends": [dict(row) for row in monthly_trends]
            }
            
        except Exception as e:
            logger.error(f"Erreur analytics ventes: {e}")
            return {}
        finally:
            conn.close()
    
    @staticmethod
    def get_inventory_analytics():
        """Statistiques d'inventaire et catalogue"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Répartition par type d'œuvre
            cursor.execute("""
                SELECT type, COUNT(*) as count,
                       SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) as available
                FROM artworks
                GROUP BY type
            """)
            artwork_types = cursor.fetchall()
            
            # Œuvres par gamme de prix
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN price < 100 THEN '< 100€'
                        WHEN price < 500 THEN '100-500€'
                        WHEN price < 1000 THEN '500-1000€'
                        ELSE '> 1000€'
                    END as price_range,
                    COUNT(*) as count
                FROM artworks
                WHERE is_available = 1
                GROUP BY price_range
            """)
            price_ranges = cursor.fetchall()
            
            return {
                "artwork_types": [dict(row) for row in artwork_types],
                "price_ranges": [dict(row) for row in price_ranges]
            }
            
        except Exception as e:
            logger.error(f"Erreur analytics inventaire: {e}")
            return {}
        finally:
            conn.close()
    
    @staticmethod
    def get_performance_metrics():
        """Métriques de performance du site (anonymisées)"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Taux de conversion approximatif (commandes vs œuvres vues)
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT id) as total_orders,
                    (SELECT COUNT(*) FROM artworks WHERE is_available = 0) as sold_artworks,
                    (SELECT COUNT(*) FROM artworks) as total_artworks
                FROM orders
                WHERE created_at >= DATE('now', '-30 days')
            """)
            conversion_data = cursor.fetchone()
            
            # Fréquence des commandes
            cursor.execute("""
                SELECT 
                    AVG(julianday('now') - julianday(created_at)) as avg_days_since_last_order
                FROM orders
                WHERE created_at >= DATE('now', '-90 days')
            """)
            order_frequency = cursor.fetchone()
            
            return {
                "conversion_data": dict(conversion_data) if conversion_data else {},
                "avg_days_between_orders": order_frequency[0] if order_frequency else 0
            }
            
        except Exception as e:
            logger.error(f"Erreur métriques performance: {e}")
            return {}
        finally:
            conn.close()

    @staticmethod
    def get_comprehensive_dashboard_analytics():
        """Combine toutes les analytics pour le dashboard"""
        return {
            "sales": PrivacyFriendlyAnalytics.get_sales_analytics(),
            "inventory": PrivacyFriendlyAnalytics.get_inventory_analytics(),
            "performance": PrivacyFriendlyAnalytics.get_performance_metrics(),
            "last_updated": datetime.now().isoformat()
        }
