import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

st.set_page_config(page_title="BrandLuxJP Suite: Calculator, Watchlist & Ledger", page_icon="🏷️", layout="wide")

# ==========================================
# DATABASE SETUP & CRUD (SQLite)
# ==========================================
def init_db():
    conn = sqlite3.connect("resale_inventory.db")
    c = conn.cursor()
    # Active Inventory Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            category TEXT,
            purchase_date TEXT,
            hammer_jpy REAL,
            landed_cost_usd REAL,
            status TEXT,
            sold_price_usd REAL,
            net_profit_usd REAL
        )
    """)
    # Watchlist Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            category TEXT,
            item_url TEXT,
            target_bid_jpy REAL,
            est_landed_usd REAL,
            est_resale_usd REAL,
            est_profit_usd REAL,
            notes TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Inventory Database Helpers ---
def add_inventory_item(name, category, hammer, landed, p_date=None):
    if not p_date:
        p_date = str(date.today())
    conn = sqlite3.connect("resale_inventory.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO inventory (item_name, category, purchase_date, hammer_jpy, landed_cost_usd, status, sold_price_usd, net_profit_usd)
        VALUES (?, ?, ?, ?, ?, 'In Stock', 0.0, 0.0)
    """, (name, category, p_date, hammer, landed))
    conn.commit()
    conn.close()

def delete_inventory_item(item_id):
    conn = sqlite3.connect("resale_inventory.db")
    c = conn.cursor()
    c.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def update_item_sale(item_id, sold_price, net_profit):
    conn = sqlite3.connect("resale_inventory.db")
    c = conn.cursor()
    c.execute("""
        UPDATE inventory 
        SET status = 'Sold', sold_price_usd = ?, net_profit_usd = ?
        WHERE id = ?
    """, (sold_price, net_profit, item_id))
    conn.commit()
    conn.close()

def get_inventory_df():
    conn = sqlite3.connect("resale_inventory.db")
    df = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()
    return df

# --- Watchlist Database Helpers ---
def add_watchlist_item(name, category, url, bid_jpy, landed, resale, profit, notes):
    conn = sqlite3.connect("resale_inventory.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO watchlist (item_name, category, item_url, target_bid_jpy, est_landed_usd, est_resale_usd, est_profit_usd, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Watching')
    """, (name, category, url, bid_jpy, landed, resale, profit, notes))
    conn.commit()
    conn.close()

def delete_watchlist_item(item_id):
    conn = sqlite3.connect("resale_inventory.db")
    c = conn.cursor()
    c.execute("DELETE FROM watchlist WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def update_watchlist_status(item_id, status):
    conn = sqlite3.connect("resale_inventory.db")
    c = conn.cursor()
    c.execute("UPDATE watchlist SET status = ? WHERE id = ?", (status, item_id))
    conn.commit()
    conn.close()

def get_watchlist_df():
    conn = sqlite3.connect("resale_inventory.db")
    df = pd.read_sql_query("SELECT * FROM watchlist", conn)
    conn.close()
    return df

# ==========================================
# APPLICATION TABS
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "🏷️ Calculator & Bid Planner", 
    "👀 Watchlist (Add / Edit / Delete)", 
    "📊 Inventory Ledger (Add / Edit / Delete)"
])

# ------------------------------------------
# TAB 1: CALCULATOR
# ------------------------------------------
with tab1:
    st.title("🏷️ Japan Auction Landed Cost & Profit Calculator")
    st.caption("Custom-tailored for BrandLuxJP fee schedules, US tariffs, and multi-platform resale margins.")

    st.sidebar.header("⚙️ Global Settings")
    jpy_rate = st.sidebar.number_input("USD/JPY Exchange Rate", min_value=100.0, max_value=250.0, value=155.0, step=0.5)
    tax_reserve_rate = st.sidebar.slider("Tax Reserve (Self-Employment + Fed/OK State)", 0, 40, 28) / 100.0

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("1. Auction Acquisition")
        item_name = st.text_input("Item Name / Description", value="Canon IXY Digicam / Lot")
        item_url = st.text_input("Auction Item URL", placeholder="https://brandlux.jp/auction/item/...")
        
        auction_format = st.selectbox(
            "Auction Format",
            ["Brand / Low Price (BA / LP)", "RealTime / TimeLimit (RT / TL)", "BA Global (BAG)"]
        )
        
        membership = st.selectbox("Membership Tier", ["Regular Member", "Premium Member"])
        item_type = st.selectbox("Product Category", ["Watches", "Electronics / Collectibles / Toys", "Apparel / Clothing", "General / Other"])
        payment_method = st.radio("Payment Method", ["Credit Card / Wallet", "Bank Transfer (-3% fee reduction)"], horizontal=True)
        
        hammer_price_jpy = st.number_input("Winning / Max Bid (JPY)", min_value=1000, value=6000, step=500)
        
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
        watchlist_notes = st.text_area("Watchlist Inspection Notes (e.g., Condition B, clean lens, needs battery)", "")

    # Calculation Logic
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
        if hammer_price_jpy <= 10000: base_pct, fixed = (0.14, 500) if is_premium else (0.17, 500)
        elif hammer_price_jpy <= 50000: base_pct, fixed = (0.14, 1000) if is_premium else (0.17, 1000)
        elif hammer_price_jpy <= 99000: base_pct, fixed = (0.13, 2000) if is_premium else (0.16, 2000)
        elif hammer_price_jpy <= 499999: base_pct, fixed = (0.13, 4000) if is_premium else (0.16, 4000)
        elif hammer_price_jpy <= 999999: base_pct, fixed = (0.12, 8000) if is_premium else (0.15, 8000)
        else: base_pct, fixed = (0.11, 10000) if is_premium else (0.14, 10000)
            
        fee_pct = max(0.0, base_pct - rate_discount)
        auction_fee_jpy = max(min_fee, (hammer_price_jpy * fee_pct) + fixed)

    else:  # BA Global
        min_fee = 800
        if hammer_price_jpy <= 49999: base_pct = 0.13 if is_premium else 0.15
        elif hammer_price_jpy <= 199999: base_pct = 0.12 if is_premium else 0.14
        elif hammer_price_jpy <= 499999: base_pct = 0.11 if is_premium else 0.13
        elif hammer_price_jpy <= 999999: base_pct = 0.10 if is_premium else 0.12
        else: base_pct = 0.09 if is_premium else 0.11
            
        fee_pct = max(0.0, base_pct - rate_discount)
        auction_fee_jpy = max(min_fee, hammer_price_jpy * fee_pct)

    # Landed Cost
    total_jpy = hammer_price_jpy + auction_fee_jpy + domestic_jpy
    item_cost_usd = (total_jpy / jpy_rate) * 1.035
    customs_duty_usd = (hammer_price_jpy / jpy_rate) * tariff_rate
    total_landed_cost_usd = item_cost_usd + intl_shipping_usd + carrier_brokerage_usd + customs_duty_usd

    # Resale & Profit
    selling_fees_usd = (expected_sale_usd * platform_fee_pct) + 0.40
    net_payout_usd = expected_sale_usd - selling_fees_usd - outbound_shipping_usd
    pretax_profit_usd = net_payout_usd - total_landed_cost_usd
    tax_amount_usd = max(0.0, pretax_profit_usd * tax_reserve_rate)
    net_in_pocket_usd = pretax_profit_usd - tax_amount_usd
    net_margin_pct = (pretax_profit_usd / expected_sale_usd) * 100 if expected_sale_usd > 0 else 0
    roi_pct = (pretax_profit_usd / total_landed_cost_usd) * 100 if total_landed_cost_usd > 0 else 0

    st.divider()
    st.subheader("📊 Cost & Profit Breakdown")

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

    st.write("")
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("👀 Add to Watchlist (Potential Purchase)", use_container_width=True):
            add_watchlist_item(item_name, item_type, item_url, hammer_price_jpy, total_landed_cost_usd, expected_sale_usd, pretax_profit_usd, watchlist_notes)
            st.success(f"Added **{item_name}** to your Watchlist!")
    with btn_col2:
        if st.button("💾 Save as Active Purchase to Inventory", type="primary", use_container_width=True):
            add_inventory_item(item_name, item_type, hammer_price_jpy, total_landed_cost_usd)
            st.success(f"Added **{item_name}** to your active inventory ledger!")

# ------------------------------------------
# TAB 2: WATCHLIST (ADD / EDIT / DELETE)
# ------------------------------------------
with tab2:
    st.header("👀 Watchlist & Potential Purchases")
    w_df = get_watchlist_df()

    # Manual Add Form
    with st.expander("➕ Manually Add an Item to Watchlist", expanded=False):
        with st.form("manual_watchlist_add"):
            w_c1, w_c2, w_c3 = st.columns(3)
            with w_c1:
                mw_name = st.text_input("Item Name / Description*")
                mw_cat = st.selectbox("Category", ["Toys / Collectibles / Tamagotchi", "Cameras / Electronics", "Pens / Small Goods", "Watches", "Wallets / Luxury Goods", "Apparel"])
            with w_c2:
                mw_url = st.text_input("Auction Item URL")
                mw_bid = st.number_input("Target Bid (JPY)", min_value=100, value=5000, step=500)
            with w_c3:
                mw_landed = st.number_input("Est. Landed Cost ($ USD)", min_value=1.0, value=50.0, step=5.0)
                mw_resale = st.number_input("Est. Resale Price ($ USD)", min_value=1.0, value=120.0, step=5.0)
            
            mw_notes = st.text_area("Notes", placeholder="Condition, battery tests, etc.")
            
            if st.form_submit_button("Add Item to Watchlist"):
                if mw_name.strip():
                    mw_profit = mw_resale - (mw_resale * 0.135 + 5.50) - mw_landed
                    add_watchlist_item(mw_name, mw_cat, mw_url, mw_bid, mw_landed, mw_resale, mw_profit, mw_notes)
                    st.success(f"Added **{mw_name}** to Watchlist!")
                    st.rerun()
                else:
                    st.error("Please enter an item name.")

    # Status Update & Transfer
    active_watch = w_df[w_df["status"] == "Watching"] if not w_df.empty else pd.DataFrame()
    if not active_watch.empty:
        with st.expander("⚡ Status Actions: Won Auction or Passed?", expanded=True):
            w_col1, w_col2, w_col3 = st.columns([2, 1, 1])
            watch_options = {
                row["id"]: f"#{row['id']} - {row['item_name']} (Target: ¥{row['target_bid_jpy']:,.0f})"
                for _, row in active_watch.iterrows()
            }
            with w_col1:
                sel_watch_id = st.selectbox("Select Tracked Lot", options=list(watch_options.keys()), format_func=lambda x: watch_options[x])
            with w_col2:
                st.write("")
                st.write("")
                if st.button("✅ Won Auction! (Move to Inventory)", type="primary"):
                    target_row = active_watch[active_watch["id"] == sel_watch_id].iloc[0]
                    add_inventory_item(target_row["item_name"], target_row["category"], target_row["target_bid_jpy"], target_row["est_landed_usd"])
                    update_watchlist_status(sel_watch_id, "Won & Transferred")
                    st.success(f"Moved #{sel_watch_id} into Inventory!")
                    st.rerun()
            with w_col3:
                st.write("")
                st.write("")
                if st.button("❌ Mark Outbid / Passed"):
                    update_watchlist_status(sel_watch_id, "Outbid/Passed")
                    st.info("Item marked as Outbid/Passed.")
                    st.rerun()

    # Delete Item from Watchlist
    if not w_df.empty:
        with st.expander("🗑️ Delete an Item from Watchlist", expanded=False):
            del_w_options = {row["id"]: f"#{row['id']} - {row['item_name']} ({row['status']})" for _, row in w_df.iterrows()}
            del_w_id = st.selectbox("Select Lot to Remove", options=list(del_w_options.keys()), format_func=lambda x: del_w_options[x])
            if st.button("Permanently Delete from Watchlist", type="primary"):
                delete_watchlist_item(del_w_id)
                st.warning(f"Deleted #{del_w_id} from your watchlist.")
                st.rerun()

    # Display Table
    st.subheader("📋 Tracked Watchlist Lots")
    if w_df.empty:
        st.info("Your watchlist is currently empty.")
    else:
        st.dataframe(
            w_df[["id", "item_name", "category", "item_url", "target_bid_jpy", "est_landed_usd", "est_resale_usd", "est_profit_usd", "status", "notes"]],
            column_config={
                "id": "ID",
                "item_name": "Item Description",
                "category": "Category",
                "item_url": st.column_config.LinkColumn("Auction URL", display_text="Open Listing 🔗"),
                "target_bid_jpy": st.column_config.NumberColumn("Target Bid (JPY)", format="¥%d"),
                "est_landed_usd": st.column_config.NumberColumn("Est. Landed ($)", format="$%.2f"),
                "est_resale_usd": st.column_config.NumberColumn("Target Resale ($)", format="$%.2f"),
                "est_profit_usd": st.column_config.NumberColumn("Est. Profit ($)", format="$%.2f"),
                "status": "Watch Status",
                "notes": "Inspection Notes",
            },
            hide_index=True,
            width="stretch"
        )

# ------------------------------------------
# TAB 3: INVENTORY LEDGER (ADD / EDIT / DELETE)
# ------------------------------------------
with tab3:
    st.header("Inventory & Sales Ledger")
    df = get_inventory_df()

    # Manual Add Form
    with st.expander("➕ Manually Add an In-Stock Purchase", expanded=False):
        with st.form("manual_inventory_add"):
            i_c1, i_c2, i_c3 = st.columns(3)
            with i_c1:
                mi_name = st.text_input("Item Name / Lot Description*")
                mi_cat = st.selectbox("Category", ["Toys / Collectibles / Tamagotchi", "Cameras / Electronics", "Pens / Small Goods", "Watches", "Wallets / Luxury Goods", "Apparel"])
            with i_c2:
                mi_date = st.date_input("Purchase Date", value=date.today())
                mi_hammer = st.number_input("Winning Bid (JPY)", min_value=0, value=6000, step=500)
            with i_c3:
                mi_landed = st.number_input("Total Landed Cost ($ USD)*", min_value=1.0, value=55.0, step=5.0)
            
            if st.form_submit_button("Save Item to Inventory"):
                if mi_name.strip():
                    add_inventory_item(mi_name, mi_cat, mi_hammer, mi_landed, str(mi_date))
                    st.success(f"Added **{mi_name}** directly to inventory!")
                    st.rerun()
                else:
                    st.error("Please enter an item name.")

    if not df.empty:
        total_invested = df["landed_cost_usd"].sum()
        sold_df = df[df["status"] == "Sold"]
        total_sold_rev = sold_df["sold_price_usd"].sum()
        total_realized_profit = sold_df["net_profit_usd"].sum()
        net_after_tax = total_realized_profit * (1.0 - tax_reserve_rate)

        st.subheader("📈 Portfolio Overview")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Capital Deployed", f"${total_invested:,.2f}")
        kpi2.metric("Gross Sales", f"${total_sold_rev:,.2f}")
        kpi3.metric("Realized Pre-Tax Profit", f"${total_realized_profit:,.2f}")
        kpi4.metric(f"Net in Pocket (~{int(tax_reserve_rate*100)}% Tax)", f"${net_after_tax:,.2f}")

        st.divider()

        # Sale Logger & Delete Row
        c_sale, c_del = st.columns([1.5, 1])

        with c_sale:
            st.subheader("📝 Record a Completed Sale")
            in_stock_items = df[df["status"] == "In Stock"]
            if not in_stock_items.empty:
                item_options = {
                    row["id"]: f"#{row['id']} - {row['item_name']} (Landed: ${row['landed_cost_usd']:.2f})" 
                    for _, row in in_stock_items.iterrows()
                }
                selected_id = st.selectbox("Select Sold Lot", options=list(item_options.keys()), format_func=lambda x: item_options[x])
                actual_sale_price = st.number_input("Final Sale Price ($ USD)", min_value=1.0, value=120.0, step=5.0)
                
                platform_deduction = (actual_sale_price * platform_fee_pct) + 0.40
                lot_cost = in_stock_items.loc[in_stock_items["id"] == selected_id, "landed_cost_usd"].values[0]
                actual_net_profit = actual_sale_price - platform_deduction - outbound_shipping_usd - lot_cost
                
                if st.button("Confirm Sale", type="primary"):
                    update_item_sale(selected_id, actual_sale_price, actual_net_profit)
                    st.success("Item updated to 'Sold'!")
                    st.rerun()
            else:
                st.success("All logged inventory is currently marked as Sold!")

        with c_del:
            st.subheader("🗑️ Delete Inventory Lot")
            del_inv_options = {row["id"]: f"#{row['id']} - {row['item_name']} ({row['status']})" for _, row in df.iterrows()}
            del_inv_id = st.selectbox("Select Lot to Permanently Remove", options=list(del_inv_options.keys()), format_func=lambda x: del_inv_options[x])
            st.write("")
            if st.button("Permanently Delete Item", type="secondary"):
                delete_inventory_item(del_inv_id)
                st.warning(f"Deleted #{del_inv_id} from inventory.")
                st.rerun()

        st.divider()
        st.subheader("📋 Complete Inventory Table")
        st.dataframe(
            df[["id", "item_name", "category", "purchase_date", "hammer_jpy", "landed_cost_usd", "status", "sold_price_usd", "net_profit_usd"]],
            column_config={
                "id": "Lot ID",
                "item_name": "Item Description",
                "category": "Category",
                "purchase_date": "Purchase Date",
                "hammer_jpy": st.column_config.NumberColumn("Winning Bid (JPY)", format="¥%d"),
                "landed_cost_usd": st.column_config.NumberColumn("Landed Cost", format="$%.2f"),
                "status": "Status",
                "sold_price_usd": st.column_config.NumberColumn("Sold Price", format="$%.2f"),
                "net_profit_usd": st.column_config.NumberColumn("Realized Profit", format="$%.2f"),
            },
            hide_index=True,
            width="stretch"
        )
    else:
st.info("No purchases logged yet. Calculate and log items from Tab 1, win an item from your Watchlist, or manually add an item above.")
