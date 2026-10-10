from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = PROJECT_DIR / "visualizations"

orders = pd.read_csv(DATA_DIR / "orders.csv")

orders["payment_method"] = (
    orders["payment_method"]
    .str.strip()
    .str.upper()
)

duplicate_mask = orders.duplicated(
    subset=[
        "customer_id",
        "product_id",
        "order_date",
        "quantity",
        "discount_pct",
        "payment_method",
        "rating",
        "returned"
    ],
    keep="first"
)

orders_clean = orders.loc[~duplicate_mask].copy()

return_rate = (
    orders_clean.groupby("payment_method")["returned"]
    .mean()
    .mul(100)
    .round(1)
    .sort_values(ascending=False)
)

print(return_rate)

plt.figure(figsize=(8, 5))

bars = plt.bar(return_rate.index, return_rate.values)

plt.xlabel("Payment Method")
plt.ylabel("Return Rate (%)")
plt.title("COD Returns at 44.4% — 3x Card")

for bar, value in zip(bars, return_rate.values):
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        f"{value:.1f}%",
        ha="center",
        va="bottom"
    )

plt.tight_layout()

OUTPUT_DIR.mkdir(exist_ok=True)

plt.savefig(
    OUTPUT_DIR / "return_rate_by_payment.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()



# Load customers and products for monthly revenue calculation
customers = pd.read_csv(DATA_DIR / "customers.csv")
products = pd.read_csv(DATA_DIR / "products.csv")

# Merge orders with customer and product data
merged_orders = orders_clean.merge(
    customers,
    how="left",
    on="customer_id"
)

merged_orders = merged_orders.merge(
    products,
    how="left",
    on="product_id"
)

# Fill missing discount values
merged_orders["discount_pct"] = merged_orders["discount_pct"].fillna(0)

# Calculate order value
merged_orders["order_value"] = (
    merged_orders["quantity"]
    * merged_orders["price"]
    * (1 - merged_orders["discount_pct"] / 100)
)

# Identify quantity outliers using the IQR method
q1 = merged_orders["quantity"].quantile(0.25)
q3 = merged_orders["quantity"].quantile(0.75)
iqr = q3 - q1

lower_bound = q1 - 1.5 * iqr
upper_bound = q3 + 1.5 * iqr

merged_orders["is_outlier"] = (
    (merged_orders["quantity"] < lower_bound)
    | (merged_orders["quantity"] > upper_bound)
)

# Convert order_date to datetime and create year-month
merged_orders["order_date"] = pd.to_datetime(merged_orders["order_date"])
merged_orders["year_month"] = (
    merged_orders["order_date"]
    .dt.to_period("M")
    .astype(str)
)

# Calculate monthly revenue excluding outliers
monthly_revenue = (
    merged_orders.loc[~merged_orders["is_outlier"]]
    .groupby("year_month")["order_value"]
    .sum()
    .round(2)
)

# Create line chart
plt.figure(figsize=(9, 5))

plt.plot(
    monthly_revenue.index,
    monthly_revenue.values,
    marker="o"
)

plt.xlabel("Month")
plt.ylabel("Revenue (INR)")
plt.title("Monthly Revenue Trend — March 2026 Peak")

plt.tight_layout()

plt.savefig(
    OUTPUT_DIR / "monthly_revenue_trend.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()