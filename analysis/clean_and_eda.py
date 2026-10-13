from pathlib import Path
import json
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

# Task 1: Load and inspect data
customers = pd.read_csv(DATA_DIR / "customers.csv")
products = pd.read_csv(DATA_DIR / "products.csv")
orders = pd.read_csv(DATA_DIR / "orders.csv")
print(f"Original orders shape: {orders.shape}\n")



# Task 2: Standardize payment_method
payment_before = orders['payment_method'].unique()
print("Unique payment methods before cleaning:", payment_before)
print("Number of unique values before:", len(payment_before))
orders["payment_method"] = orders["payment_method"].str.strip().str.upper()
payments_after = orders['payment_method'].unique()
print("Unique payment methods after cleaning:", payments_after)
print("Number of unique values after:", len(payments_after))
print("Payment method counts:\n", orders['payment_method'].value_counts(),"\n")



# Task 3: Remove duplicate orders
duplicates_rows = orders.duplicated(subset = ['customer_id', 
                                             'product_id', 
                                             'order_date', 
                                             'quantity', 
                                             'discount_pct', 
                                             'payment_method', 
                                             'rating', 
                                             'returned'], 
                                   keep = "first" )
# Exclude order_id when detecting duplicates
duplicates_removed = orders.loc[duplicates_rows]
duplicate_order_ids = duplicates_removed['order_id'].tolist()
print(f"Duplicate order IDs: {duplicate_order_ids}")
print(f"Number of duplicates: {duplicates_rows.sum()}")
# Shape after removing duplicates
orders_clean = orders.loc[~duplicates_rows].copy()
print(f"Shape after removing duplicate: {orders_clean.shape}\n")


# Task 4: Impute missing values
discount_pct_missing = orders_clean['discount_pct'].isnull().sum()
print(f"missing discount_pct: {discount_pct_missing}")
orders_clean['discount_pct'] = orders_clean['discount_pct'].fillna(0)
rating_missing = orders_clean['rating'].isnull().sum()
print(f"Missing ratings before imputation: {rating_missing}")
rating_median = orders_clean['rating'].median()
print(f"Median rating: {rating_median}")
orders_clean['rating'] = orders_clean['rating'].fillna(rating_median)
print("Missing values after imputation:")
print(orders_clean[["discount_pct", "rating"]].isnull().sum())


# Task 5: Merge data and reconcile revenue
merged_orders = orders_clean.merge(customers, how='left', on='customer_id')
merged_orders = merged_orders.merge(products, how='left', on='product_id')
merged_orders["order_value"] = (
    merged_orders["quantity"]
    * merged_orders["price"]
    * (1 - merged_orders["discount_pct"] / 100))
cleaned_total_revenue = merged_orders["order_value"].sum()
print(f"\nCleaned total revenue: {cleaned_total_revenue:.2f}")
duplicates_orders_removed = duplicates_removed.merge(products, how='left', on='product_id')
duplicates_orders_removed["order_value"] = (
    duplicates_orders_removed["quantity"]
    * duplicates_orders_removed["price"]
    * (1 - duplicates_orders_removed["discount_pct"] / 100))
duplicate_total_value = duplicates_orders_removed["order_value"].sum()
print(f"Duplicate total revenue: {duplicate_total_value:.2f}")
raw_total_revenue = 99860.20
revenue_difference = raw_total_revenue - cleaned_total_revenue
assert round(duplicate_total_value, 2) == 2501.90
assert round(revenue_difference, 2) == round(duplicate_total_value, 2)
print(f"""
Revenue Reconciliation:
Part 1 SQL reported raw revenue of ₹{raw_total_revenue:.2f}.
After removing the five duplicate orders, Python calculated cleaned
revenue of ₹{cleaned_total_revenue:.2f}, a decrease of ₹{revenue_difference:.2f}.
The combined order value of the five removed duplicate rows is
₹{duplicate_total_value:.2f}, which matches the revenue difference.
This difference is attributable to removing the duplicate orders,
not to imputing missing values. Filling missing discounts with 0 is
consistent with treating a NULL discount as 0% in the SQL report,
and imputing ratings does not affect order_value because rating is
not used in the revenue calculation.
\n""")


# Task 6: IQR outlier detection
q1 = merged_orders["quantity"].quantile(0.25)
q3 = merged_orders["quantity"].quantile(0.75)
print(f"Q1: {q1:.1f}, Q3: {q3:.1f}")
iqr = q3 - q1
print(f"IQR: {iqr:.1f}")
lower_bound = q1 - 1.5 * iqr
upper_bound = q3 + 1.5 * iqr
print(f"Lower bound: {lower_bound:.1f}, Upper bound: {upper_bound:.1f}")
# Flag outliers; do not remove them
merged_orders["is_outlier"] = ((merged_orders["quantity"] < lower_bound) | (merged_orders["quantity"] > upper_bound))
outliers = merged_orders.loc[merged_orders["is_outlier"],["order_id","quantity"]]
print(outliers)
print("Number of outliers:", merged_orders["is_outlier"].sum())


# Task 7: COD return-rate hypothesis
print("\nDoes COD have a higher return rate than CARD and UPI orders?")
return_rate = orders_clean.groupby('payment_method')['returned'].agg(['count', 'mean'])
return_rate["return_rate_pct"] = (return_rate["mean"] * 100).round(1)
print(return_rate)
print("Hypothesis: Confirmed.")


# Task 8: Multi-level segmentation
multi_segment = merged_orders.groupby(['payment_method','city_tier'])['returned'].agg(['count','mean'])
multi_segment["return_rate"] = (multi_segment["mean"]*100).round(1)
highest_risk_segment = multi_segment["return_rate"].idxmax()
print(multi_segment)
highest_return_rate = multi_segment.loc[
    highest_risk_segment, "return_rate"
]
print(f"Highest-risk segment: {highest_risk_segment[0]} + "
      f"Tier {highest_risk_segment[1]} at {highest_return_rate:.1f}%\n")



# Task 9: Correlation analysis
corr = orders_clean[['rating', 'returned', 'discount_pct', 'quantity']].corr()
print(corr.round(2))

def correlation_strength(r):
    
    r = abs(r)
    if r < 0.2:
        return "negligible"
    elif r < 0.4:
        return "weak"
    elif r < 0.7:
        return "moderate"
    else:
        return "strong"

pairs = [
    ("rating", "returned"),
    ("rating", "discount_pct"),
    ("rating", "quantity"),
    ("returned", "discount_pct"),
    ("returned", "quantity"),
    ("discount_pct", "quantity"),
]

for col1, col2 in pairs:
    r = corr.loc[col1, col2]
    print(f"{col1} vs {col2}: {r:.2f} {correlation_strength(r)}")

print("Hypothesis: Higher discounts reduce returns — Busted.\n")


# Task 10: Outlier-corrected time series
merged_orders["order_date"] = pd.to_datetime(merged_orders["order_date"])

merged_orders["year_month"] = (
    merged_orders["order_date"].dt.to_period("M").astype(str)
)

monthly_revenue_with_outliers = (
    merged_orders.groupby("year_month")["order_value"]
    .sum()
    .round(2)
)

print("Monthly revenue including outliers:")
print(monthly_revenue_with_outliers)

monthly_revenue_without_outliers = (
    merged_orders.loc[~merged_orders["is_outlier"]]
    .groupby("year_month")["order_value"]
    .sum()
    .round(2)
)

print("\nMonthly revenue excluding outliers:")
print(monthly_revenue_without_outliers)

true_peak_month = monthly_revenue_without_outliers.idxmax()
true_peak_revenue = monthly_revenue_without_outliers.max()

print(
    f"\nTrue peak month after outlier correction: "
    f"{true_peak_month} with revenue ₹{true_peak_revenue:.2f}"
)

print(
    "\nJanuary's apparent revenue lead is an artifact of the two bulk "
    "outlier orders O0011 (quantity 25) and O0098 (quantity 30). "
    "After excluding these outliers, March 2026 is the genuine peak month."
)




# Part 3: Export verified findings
findings = {
    "cleaned_total_revenue_inr": round(float(cleaned_total_revenue), 2),
    "raw_total_revenue_inr": round(float(raw_total_revenue), 2),
    "duplicate_reconciliation_delta_inr": round(float(revenue_difference), 2),

    "return_rate_by_payment": {
        payment: round(float(rate), 1)
        for payment, rate in return_rate["return_rate_pct"].items()
    },

    "highest_risk_segment": {
        "payment_method": str(highest_risk_segment[0]),
        "city_tier": int(highest_risk_segment[1]),
        "return_rate_pct": round(float(highest_return_rate), 1)
    },

    "true_peak_month": {
        "month": str(true_peak_month),
        "revenue_inr": round(float(true_peak_revenue), 2)
    },

    "outlier_inflated_month": {
        "month": "2026-01",
        "apparent_revenue_inr": round(
            float(monthly_revenue_with_outliers["2026-01"]), 2
        ),
        "corrected_revenue_inr": round(
            float(monthly_revenue_without_outliers["2026-01"]), 2
        )
    }
}

NARRATOR_DIR = PROJECT_DIR / "narrator"
NARRATOR_DIR.mkdir(exist_ok=True)

findings_path = NARRATOR_DIR / "findings.json"

with open(findings_path, "w", encoding="utf-8") as f:
    json.dump(findings, f, indent=2)

print(f"Findings written to: {findings_path}")