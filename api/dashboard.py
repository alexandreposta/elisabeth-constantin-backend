from fastapi import APIRouter, Request, HTTPException
from datetime import datetime
from api.auth_admin import verify_session
from app.database import get_database

router = APIRouter()

@router.get("/dashboard/stats")
def get_dashboard_stats(request: Request):
    session_id = request.cookies.get("session_id")
    if not verify_session(session_id):
        raise HTTPException(status_code=401, detail="Session invalide")

    db = get_database()
    try:
        # --- Ventes par jour ---
        from datetime import timedelta
        import pandas as pd
        now = datetime.now()
        orders = list(db["orders"].find({"created_at": {"$gte": now - timedelta(days=30)}}))
        df_orders = pd.DataFrame(orders)
        if not df_orders.empty:
            df_orders["date"] = df_orders["created_at"].dt.date
            daily_sales = df_orders.groupby("date").agg(orders_count=("_id", "count"), daily_revenue=("total", "sum")).reset_index().to_dict("records")
        else:
            daily_sales = []

        # --- Œuvres les plus vendues ---
        items = []
        for order in orders:
            items.extend(order.get("items", []))
        df_items = pd.DataFrame(items)
        if not df_items.empty:
            df_items = df_items.merge(pd.DataFrame(list(db["artworks"].find())), left_on="artwork_id", right_on="_id", suffixes=("", "_artwork"))
            popular_artworks = df_items.groupby(["artwork_id", "title"]).size().reset_index(name="sales_count").sort_values("sales_count", ascending=False).head(10).to_dict("records")
        else:
            popular_artworks = []

        # --- Tendances mensuelles ---
        if not df_orders.empty:
            df_orders["month"] = df_orders["created_at"].dt.strftime('%Y-%m')
            monthly_trends = df_orders.groupby("month").agg(orders=("_id", "count"), revenue=("total", "sum"), avg_order_value=("total", "mean")).reset_index().to_dict("records")
        else:
            monthly_trends = []

        # --- Répartition des œuvres par type ---
        artworks = list(db["artworks"].find())
        df_artworks = pd.DataFrame(artworks)
        if not df_artworks.empty:
            artwork_types = df_artworks.groupby("type").agg(count=("_id", "count"), available=("is_available", "sum")).reset_index().to_dict("records")
        else:
            artwork_types = []

        # --- Œuvres par gamme de prix ---
        if not df_artworks.empty:
            def price_range(price):
                if price < 100:
                    return "< 100€"
                elif price < 500:
                    return "100-500€"
                elif price < 1000:
                    return "500-1000€"
                else:
                    return "> 1000€"
            df_artworks["price_range"] = df_artworks["price"].apply(price_range)
            price_ranges = df_artworks[df_artworks["is_available"] == True].groupby("price_range").size().reset_index(name="count").to_dict("records")
        else:
            price_ranges = []

        # --- Métriques de conversion et fréquence ---
        total_orders = len(orders)
        sold_artworks = df_artworks[df_artworks["is_available"] == False].shape[0] if not df_artworks.empty else 0
        total_artworks = df_artworks.shape[0] if not df_artworks.empty else 0
        conversion_data = {
            "total_orders": total_orders,
            "sold_artworks": sold_artworks,
            "total_artworks": total_artworks
        }

        if not df_orders.empty:
            df_orders["days_since_order"] = (now - df_orders["created_at"]).dt.days
            avg_days_between_orders = df_orders["days_since_order"].mean()
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
        raise HTTPException(status_code=500, detail=f"Erreur dashboard: {str(e)}")
