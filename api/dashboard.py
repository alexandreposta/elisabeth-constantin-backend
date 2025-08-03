from fastapi import APIRouter, Request, HTTPException
from datetime import datetime, timedelta
from api.auth_admin import verify_session
from app.database import get_database
from collections import defaultdict

router = APIRouter()

@router.get("/dashboard/stats")
def get_dashboard_stats(request: Request):
    session_id = request.cookies.get("session_id")
    if not verify_session(session_id):
        raise HTTPException(status_code=401, detail="Session invalide")

    try:
        db = get_database()
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        
        # --- Récupération des données ---
        orders = list(db["orders"].find({"created_at": {"$gte": thirty_days_ago}}))
        artworks = list(db["artworks"].find())
        
        # --- Ventes par jour ---
        daily_sales_data = defaultdict(lambda: {"orders_count": 0, "daily_revenue": 0})
        for order in orders:
            if "created_at" in order:
                date_key = order["created_at"].date().isoformat()
                daily_sales_data[date_key]["orders_count"] += 1
                daily_sales_data[date_key]["daily_revenue"] += order.get("total", 0)
        
        daily_sales = [
            {"date": date, **data} 
            for date, data in daily_sales_data.items()
        ]
        
        # --- Œuvres les plus vendues ---
        artwork_sales = defaultdict(int)
        artwork_names = {}
        
        # Créer un mapping des artwork_id vers les noms
        for artwork in artworks:
            artwork_names[str(artwork["_id"])] = artwork.get("title", "Sans titre")
        
        # Compter les ventes par artwork
        for order in orders:
            for item in order.get("items", []):
                artwork_id = str(item.get("artwork_id", ""))
                artwork_sales[artwork_id] += item.get("quantity", 1)
        
        popular_artworks = [
            {
                "artwork_id": artwork_id,
                "title": artwork_names.get(artwork_id, "Inconnu"),
                "sales_count": count
            }
            for artwork_id, count in sorted(artwork_sales.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # --- Tendances mensuelles ---
        monthly_data = defaultdict(lambda: {"orders": 0, "revenue": 0, "total_amount": 0})
        for order in orders:
            if "created_at" in order:
                month_key = order["created_at"].strftime('%Y-%m')
                monthly_data[month_key]["orders"] += 1
                total = order.get("total", 0)
                monthly_data[month_key]["revenue"] += total
                monthly_data[month_key]["total_amount"] += total
        
        monthly_trends = []
        for month, data in monthly_data.items():
            avg_order_value = data["revenue"] / data["orders"] if data["orders"] > 0 else 0
            monthly_trends.append({
                "month": month,
                "orders": data["orders"],
                "revenue": data["revenue"],
                "avg_order_value": avg_order_value
            })
        
        # --- Répartition des œuvres par type ---
        type_data = defaultdict(lambda: {"count": 0, "available": 0})
        for artwork in artworks:
            artwork_type = artwork.get("type", "Autre")
            type_data[artwork_type]["count"] += 1
            if artwork.get("is_available", False):
                type_data[artwork_type]["available"] += 1
        
        artwork_types = [
            {"type": type_name, **data} 
            for type_name, data in type_data.items()
        ]
        
        # --- Répartition par gammes de prix ---
        price_ranges = {"0-100": 0, "100-500": 0, "500-1000": 0, "1000+": 0}
        for artwork in artworks:
            price = artwork.get("price", 0)
            if price < 100:
                price_ranges["0-100"] += 1
            elif price < 500:
                price_ranges["100-500"] += 1
            elif price < 1000:
                price_ranges["500-1000"] += 1
            else:
                price_ranges["1000+"] += 1
        
        price_ranges = [
            {"range": range_name, "count": count} 
            for range_name, count in price_ranges.items()
        ]
        
        # --- Données de performance simple ---
        total_artworks = len(artworks)
        total_orders = len(orders)
        conversion_data = {
            "total_artworks": total_artworks,
            "total_orders": total_orders,
            "conversion_rate": (total_orders / total_artworks * 100) if total_artworks > 0 else 0
        }
        
        # --- Moyenne des jours entre commandes ---
        if len(orders) > 1:
            order_dates = [order["created_at"] for order in orders if "created_at" in order]
            order_dates.sort()
            days_between = []
            for i in range(1, len(order_dates)):
                diff = (order_dates[i] - order_dates[i-1]).days
                days_between.append(diff)
            avg_days_between_orders = sum(days_between) / len(days_between) if days_between else 0
        else:
            avg_days_between_orders = 0
        return {
            "sales": {
                "daily_sales": daily_sales,
                "popular_artworks": popular_artworks,
                "monthly_trends": monthly_trends,
            },
            "inventory": {
                "artwork_types": artwork_types,
                "price_ranges": price_ranges,
            },
            "performance": {
                "conversion_data": conversion_data,
                "avg_days_between_orders": avg_days_between_orders
            },
            "last_updated": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"Erreur dashboard: {str(e)}")  # Pour debug
        raise HTTPException(status_code=500, detail=f"Erreur dashboard: {str(e)}")
