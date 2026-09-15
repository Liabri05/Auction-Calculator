import streamlit as st

st.set_page_config(page_title="BrandLuxJP Landed Cost Calculator", page_icon="🏷️", layout="wide")

st.title("🏷️ Japan Auction Landed Cost & Profit Calculator")
st.caption("Custom-tailored for BrandLuxJP fee schedules, US tariffs, and multi-platform resale margins.")

# Sidebar - Global Assumptions
st.sidebar.header("⚙️ Global Settings")
jpy_rate = st.sidebar.number_input("USD/JPY Exchange Rate", min_value=100.0, max_value=250.0, value=155.0, step=0.5)
tax_reserve_rate = st.sidebar.slider("Tax Reserve (Self-Employment + Fed/OK State)", 0, 40, 28) / 100.0

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("1. Auction Acquisition")
    
    auction_format = st.selectbox(
        "Auction Format",
        ["Brand / Low Price (BA / LP)", "RealTime / TimeLimit (RT / TL)", "BA Global (BAG)"]
    )
    
    membership = st.selectbox("Membership Tier", ["Regular Member", "Premium Member"])
    item_type = st.selectbox("Product Category", ["Watches", "Electronics / Collectibles / Toys", "Apparel / Clothing", "General / Other"])
    payment_method = st.radio("Payment Method", ["Credit Card / Wallet", "Bank Transfer (-3% fee reduction)"], horizontal=True)
    
    hammer_price_jpy = st.number_input("Winning Bid (JPY)", min_value=1000, value=6000, step=500)
    
    st.subheader("2. Inbound Logistics & Import Fees")
    c_ship1, c_ship2 = st.columns(2)
    with c_ship1:
        domestic_jpy = st.number_input("Domestic JP Transit (JPY)", value=800, step=100)
        intl_shipping_usd = st.number_input("International Shipping Share ($)", value=8.0, step=1.0)
    with c_ship2:
        carrier_brokerage_usd = st.number_input("Carrier Entry Fee Share ($)", value=3.0, step=0.5)
        tariff_rate = st.number_input(
            "Estimated Tariff / Duty %",
            value=16.0 if item_type == "Apparel / Clothing" else (2.0 if item_type == "Electronics / Collectibles / Toys" else 8.0),
            step=1.0
        ) / 100.0

with col2:
    st.subheader("3. US Resale Target")
    expected_sale_usd = st.number_input("Target US Resale Price ($)", min_value=5.0, value=140.0, step=5.0)
    platform_fee_pct = st.number_input("Platform Fee % (eBay ~13.5%, Poshmark 20%)", value=13.5, step=0.5) / 100.0
    outbound_shipping_usd = st.number_input("Domestic US Outbound Shipping ($)", value=6.50, step=0.5)

# --- Calculation Logic ---

# 1. Auction Fee Schedule
is_bank_transfer = "Bank Transfer" in payment_method
is_premium = "Premium" in membership
rate_discount = 0.03 if is_bank_transfer else 0.0

if auction_format == "Brand / Low Price (BA / LP)":
    min_fee = 600
    if is_premium:
        fee_pct = max(0.0, 0.15 - rate_discount)
    elif item_type == "Watches":
        fee_pct = max(0.0, 0.17 - rate_discount)
    else:
        fee_pct = max(0.0, 0.18 - rate_discount)
    auction_fee_jpy = max(min_fee, hammer_price_jpy * fee_pct)

elif auction_format == "RealTime / TimeLimit (RT / TL)":
    min_fee = 800
    if hammer_price_jpy <= 10000:
        base_pct, fixed = (0.14, 500) if is_premium else (0.17, 500)
    elif hammer_price_jpy <= 50000:
        base_pct, fixed = (0.14, 1000) if is_premium else (0.17, 1000)
    elif hammer_price_jpy <= 99000:
        base_pct, fixed = (0.13, 2000) if is_premium else (0.16, 2000)
    elif hammer_price_jpy <= 499999:
        base_pct, fixed = (0.13, 4000) if is_premium else (0.16, 4000)
    elif hammer_price_jpy <= 999999:
        base_pct, fixed = (0.12, 8000) if is_premium else (0.15, 8000)
    else:
        base_pct, fixed = (0.11, 10000) if is_premium else (0.14, 10000)
        
    fee_pct = max(0.0, base_pct - rate_discount)
    calculated_fee = (hammer_price_jpy * fee_pct) + fixed
    auction_fee_jpy = max(min_fee, calculated_fee)

else:  # BA Global
    min_fee = 800
    if hammer_price_jpy <= 49999:
        base_pct = 0.13 if is_premium else 0.15
    elif hammer_price_jpy <= 199999:
        base_pct = 0.12 if is_premium else 0.14
    elif hammer_price_jpy <= 499999:
        base_pct = 0.11 if is_premium else 0.13
    elif hammer_price_jpy <= 999999:
        base_pct = 0.10 if is_premium else 0.12
    else:
        base_pct = 0.09 if is_premium else 0.11
        
    fee_pct = max(0.0, base_pct - rate_discount)
    auction_fee_jpy = max(min_fee, hammer_price_jpy * fee_pct)

# 2. Landed Cost USD
total_jpy = hammer_price_jpy + auction_fee_jpy + domestic_jpy
fx_fee_rate = 0.035  # Card/wire spread
item_cost_usd = (total_jpy / jpy_rate) * (1 + fx_fee_rate)
customs_duty_usd = (hammer_price_jpy / jpy_rate) * tariff_rate

total_landed_cost_usd = item_cost_usd + intl_shipping_usd + carrier_brokerage_usd + customs_duty_usd

# 3. Revenue & Profit
selling_fees_usd = (expected_sale_usd * platform_fee_pct) + 0.40
net_payout_usd = expected_sale_usd - selling_fees_usd - outbound_shipping_usd
pretax_profit_usd = net_payout_usd - total_landed_cost_usd
tax_amount_usd = max(0.0, pretax_profit_usd * tax_reserve_rate)
net_in_pocket_usd = pretax_profit_usd - tax_amount_usd
net_margin_pct = (pretax_profit_usd / expected_sale_usd) * 100 if expected_sale_usd > 0 else 0
roi_pct = (pretax_profit_usd / total_landed_cost_usd) * 100 if total_landed_cost_usd > 0 else 0

# --- Presentation ---
st.divider()
st.subheader("📊 Profit & Cost Breakdown")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Landed Cost", f"${total_landed_cost_usd:,.2f}")
m2.metric("Pre-Tax Net Profit", f"${pretax_profit_usd:,.2f}")
m3.metric("Net In Pocket (Post-Tax)", f"${net_in_pocket_usd:,.2f}")
m4.metric("ROI on Capital", f"{roi_pct:.1f}%")

with st.expander("🔍 Itemized Ledger Details"):
    c_det1, c_det2 = st.columns(2)
    with c_det1:
        st.write(f"**Item Hammer Price:** ¥{hammer_price_jpy:,.0f} (~${hammer_price_jpy/jpy_rate:,.2f})")
        st.write(f"**Auction Platform Fee:** ¥{auction_fee_jpy:,.0f} (~${auction_fee_jpy/jpy_rate:,.2f})")
        st.write(f"**Domestic Japan Shipping:** ¥{domestic_jpy:,.0f} (~${domestic_jpy/jpy_rate:,.2f})")
        st.write(f"**Tariffs & Carrier Brokerage:** ${customs_duty_usd + carrier_brokerage_usd:,.2f}")
        st.write(f"**International Freight Share:** ${intl_shipping_usd:,.2f}")
    with c_det2:
        st.write(f"**Gross Marketplace Resale:** ${expected_sale_usd:,.2f}")
        st.write(f"**Marketplace Commissions:** -${selling_fees_usd:,.2f}")
        st.write(f"**Domestic US Shipping:** -${outbound_shipping_usd:,.2f}")
        st.write(f"**Estimated Taxes ({int(tax_reserve_rate*100)}%):** -${tax_amount_usd:,.2f}")
        st.write(f"**Net Profit Margin on Sale:** {net_margin_pct:.1f}%")
        