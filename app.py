import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

st.set_page_config(page_title="BrandLuxJP Landed Cost Calculator", page_icon="🏷️", layout="wide")

# ==========================================
# DATABASE SETUP (SQLite)
# ==========================================
def init_db():
    conn = sqlite3.connect("inventory_ledger.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            category TEXT,
            purchase_date TEXT,
            hammer_jpy REAL,
            landed_cost_usd REAL,
            status TEXT,
            sold_price_usd REAL,
            platform_fee_usd REAL,
            outbound_shipping_usd REAL,
            net_profit_usd REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

def insert_purchase(item_name, category, hammer_jpy, landed_cost_usd):
    conn = sqlite3.connect("inventory_ledger.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO purchases (item_name, category, purchase_date, hammer_jpy, landed_cost_usd, status, sold_price_usd, platform_fee_usd, outbound_shipping_usd, net_profit_usd)
        VALUES (?, ?, ?, ?, ?, 'In Stock', 0.0, 0.0, 0.0, 0.0)
    """, (item_name, category, str(date.today()), hammer_jpy, landed_cost_usd))
    conn.commit()
    conn.close()

def record_sale(item_id, sold_price, platform_fee, outbound_ship, net_profit):
    conn = sqlite3.connect("inventory_ledger.db")
    c = conn.cursor()
    c.execute("""
        UPDATE purchases 
        SET status = 'Sold', 
            sold_price_usd = ?, 
            platform_fee_usd = ?,
            outbound_shipping_usd = ?,
            net_profit_usd = ?
        WHERE id = ?
    """, (sold_price, platform_fee, outbound_ship, net_profit, item_id))
    conn.commit()
    conn.close()

def load_purchases_df():
    conn = sqlite3.connect("inventory_ledger.db")
    df = pd.read_sql_query("SELECT * FROM purchases", conn)
    conn.close()
    return df

# ==========================================
# APP TABS
# ==========================================
tab_calc, tab_tracker = st.tabs(["🏷️ Calculator & Purchase Logger", "📊 Inventory & Sales Tracker"])

with tab_calc:
    st.title("🏷️ Japan Auction Landed Cost & Profit Calculator")
    st.caption("Custom-tailored for BrandLuxJP fee schedules, US tariffs, and multi-platform resale margins.")

    # Sidebar - Global Assumptions
    st.sidebar.header("⚙️ Global Settings")
    jpy_rate = st.sidebar.number_input("USD/JPY Exchange Rate", min_value=100.0, max_value=250.0, value=155.0, step=0.5)
    tax_reserve_rate = st.sidebar.slider("Tax Reserve (Self-Employment + Fed/OK State)", 0, 40, 28) / 100.0

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("1. Auction Acquisition")
        item_name = st.text_input("Item Name / Lot Description", value="Canon IXY Digicam / Lot")
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

    # Purchase Logging Action
    st.divider()
    if st.button("📥 Log This Purchase into Inventory", type="primary"):
        insert_purchase(item_name, item_type, hammer_price_jpy, total_landed_cost_usd)
        st.success(f"Successfully recorded **{item_name}** with a Landed Cost of **${total_landed_cost_usd:,.2f}**!")

# ==========================================
# TAB 2: INVENTORY & SALES TRACKER
# ==========================================
with tab_tracker:
    st.title("📊 Inventory & Realized Profit Tracker")
    st.caption("Track active stock, record final marketplace sales prices, and monitor actual margins.")
    
    df = load_purchases_df()
    
    if df.empty:
        st.info("No purchases recorded yet. Use Tab 1 to calculate and log lots as you win them.")
    else:
        # High-level financial KPIs
        total_invested = df["landed_cost_usd"].sum()
        sold_items = df[df["status"] == "Sold"]
        active_items = df[df["status"] == "In Stock"]
        
        gross_sales = sold_items["sold_price_usd"].sum()
        total_net_profit = sold_items["net_profit_usd"].sum()
        overall_realized_margin = (total_net_profit / gross_sales * 100) if gross_sales > 0 else 0.0
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Capital Deployed", f"${total_invested:,.2f}")
        k2.metric("Active Units in Stock", f"{len(active_items)} units")
        k3.metric("Gross Sales Realized", f"${gross_sales:,.2f}")
        k4.metric("Total Realized Net Profit", f"${total_net_profit:,.2f}", f"{overall_realized_margin:.1f}% margin")
        
        st.divider()
        
        # Form to mark item as sold
        if not active_items.empty:
            with st.expander("🏷️ Record a Sale for an In-Stock Item", expanded=True):
                choice_map = {row["id"]: f"Lot #{row['id']} - {row['item_name']} (Landed: ${row['landed_cost_usd']:.2f})" for _, row in active_items.iterrows()}
                selected_id = st.selectbox("Select Item Sold", options=list(choice_map.keys()), format_func=lambda x: choice_map[x])
                
                c_sale1, c_sale2, c_sale3 = st.columns(3)
                with c_sale1:
                    actual_sale_price = st.number_input("Final Sale Price ($ USD)", min_value=1.0, value=140.0, step=5.0)
                with c_sale2:
                    sale_platform_fee_pct = st.number_input("Platform Fee %", value=13.5, step=0.5, key="sale_fee_pct") / 100.0
                with c_sale3:
                    actual_outbound_ship = st.number_input("Actual Outbound Shipping ($)", value=6.50, step=0.5, key="sale_outbound_ship")
                
                # Math for recorded sale
                selected_row = active_items.loc[active_items["id"] == selected_id].iloc[0]
                actual_platform_fee = (actual_sale_price * sale_platform_fee_pct) + 0.40
                actual_net_profit = actual_sale_price - actual_platform_fee - actual_outbound_ship - selected_row["landed_cost_usd"]
                
                st.caption(f"Projected Realized Profit on Lot #{selected_id}: **${actual_net_profit:,.2f}**")
                
                if st.button("Confirm & Save Sale"):
                    record_sale(selected_id, actual_sale_price, actual_platform_fee, actual_outbound_ship, actual_net_profit)
                    st.success(f"Updated Lot #{selected_id} to Sold!")
                    st.rerun()

        # Full inventory table
        st.subheader("Inventory Master Ledger")
        st.dataframe(
            df[["id", "item_name", "category", "purchase_date", "hammer_jpy", "landed_cost_usd", "status", "sold_price_usd", "net_profit_usd"]],
            column_config={
                "id": "Lot #",
                "item_name": "Item Description",
                "category": "Category",
                "purchase_date": "Logged Date",
                "hammer_jpy": st.column_config.NumberColumn("Hammer (JPY)", format="¥%d"),
                "landed_cost_usd": st.column_config.NumberColumn("Landed Cost", format="$%.2f"),
                "status": "Status",
                "sold_price_usd": st.column_config.NumberColumn("Sold Price", format="$%.2f"),
                "net_profit_usd": st.column_config.NumberColumn("Net Profit", format="$%.2f"),
            },
            hide_index=True,
            use_container_width=True
        )
        