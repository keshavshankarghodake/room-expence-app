import os
import itertools
import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Room Expense Calculator", layout="wide")

DATA_DIR = "expense_records"
os.makedirs(DATA_DIR, exist_ok=True)

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

st.title("🏠 Room Expense Calculator & Settlement")

# =================================================================
# 1. Default people
# =================================================================
if "people" not in st.session_state:
    st.session_state.people = pd.DataFrame({
        "Name":           ["Keshav", "Rajan", "Ruturaj", "Prithviraj", "Mahesh", "Vishwajit", "Shivtej"],
        "In Rent":        [True,  True,  True,  True,  True,  True,  False],
        "In Bill":        [True,  True,  True,  True,  True,  True,  True],
        "In Maid":        [True,  True,  True,  True,  True,  True,  True],
        "In Groceries":   [True,  True,  True,  True,  True,  True,  True],
        "In Water":       [True,  True,  True,  True,  True,  True,  True],
        "Groceries Paid": [0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0],
        "Water Paid":     [0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0],
    })

# =================================================================
# 2. Settings  (all at top level — no nesting, fixes electricity bug)
# =================================================================
st.subheader("1. Monthly Settings")

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    total_rent = st.number_input("Total Room Rent (₹)", min_value=0.0, value=12000.0, step=500.0)
with c2:
    prev_unit = st.number_input("Previous Meter Reading", min_value=0.0, value=None,
                                 placeholder="e.g. 1234", help="Last month's meter reading")
with c3:
    curr_unit = st.number_input("Current Meter Reading", min_value=0.0, value=None,
                                 placeholder="e.g. 1304", help="This month's meter reading")
with c4:
    rate_per_unit = st.number_input("Rate per Unit (₹)", min_value=0.0, value=15.0, step=0.5)
with c5:
    maid_per_person = st.number_input("Maid per Person (₹)", min_value=0.0, value=1200.0, step=50.0)

prev_unit = prev_unit or 0.0
curr_unit = curr_unit or 0.0
units_used       = round(max(curr_unit - prev_unit, 0.0), 4)
electricity_bill = round(units_used * rate_per_unit, 2)
owner_due        = round(total_rent + electricity_bill, 2)

if curr_unit == 0.0 and prev_unit == 0.0:
    st.warning("⚡ Enter Previous and Current meter readings to calculate electricity bill.")
elif curr_unit <= prev_unit:
    st.error(f"⚡ Current reading ({curr_unit}) must be greater than Previous ({prev_unit}). Units = 0.")
else:
    st.success(
        f"⚡ {curr_unit:g} − {prev_unit:g} = **{units_used:g} units** "
        f"× ₹{rate_per_unit:g} = **₹{electricity_bill:,.2f}**  |  "
        f"🏠 Owner due = ₹{total_rent:,.2f} + ₹{electricity_bill:,.2f} = **₹{owner_due:,.2f}**"
    )

st.divider()

# =================================================================
# 3. People table
# =================================================================
st.subheader("2. People & Participation")
st.caption("Tick/untick each cost column. Enter actual Groceries/Water spend per person.")

st.data_editor(
    st.session_state.people,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Name":           st.column_config.TextColumn(required=True),
        "In Rent":        st.column_config.CheckboxColumn("Rent?"),
        "In Bill":        st.column_config.CheckboxColumn("Elec?"),
        "In Maid":        st.column_config.CheckboxColumn("Maid?"),
        "In Groceries":   st.column_config.CheckboxColumn("Grocery?"),
        "In Water":       st.column_config.CheckboxColumn("Water?"),
        "Groceries Paid": st.column_config.NumberColumn("Grocery Paid ₹", min_value=0.0, step=1.0),
        "Water Paid":     st.column_config.NumberColumn("Water Paid ₹",   min_value=0.0, step=1.0),
    },
    key="people_editor",
)

# Read committed edits directly from session_state — avoids double-entry bug
_state = st.session_state.get("people_editor", {})
_base  = st.session_state.people.copy()

# Apply added rows
for row in _state.get("added_rows", []):
    _base = pd.concat([_base, pd.DataFrame([row])], ignore_index=True)

# Apply edited rows
for idx, changes in _state.get("edited_rows", {}).items():
    for col, val in changes.items():
        _base.at[int(idx), col] = val

# Apply deleted rows
deleted = _state.get("deleted_rows", [])
if deleted:
    _base = _base.drop(index=[int(i) for i in deleted]).reset_index(drop=True)

df = _base.dropna(subset=["Name"]).copy()
df = df[df["Name"].astype(str).str.strip() != ""].reset_index(drop=True)

if df.empty:
    st.warning("Add at least one person.")
    st.stop()

for col in ["In Rent", "In Bill", "In Maid", "In Groceries", "In Water"]:
    df[col] = df[col].fillna(False).astype(bool)
for col in ["Groceries Paid", "Water Paid"]:
    df[col] = df[col].fillna(0.0)

# =================================================================
# 4. Core calculations
# =================================================================
rent_n  = int(df["In Rent"].sum())
bill_n  = int(df["In Bill"].sum())
maid_n  = int(df["In Maid"].sum())
groc_n  = int(df["In Groceries"].sum())
water_n = int(df["In Water"].sum())

rent_share  = (total_rent       / rent_n) if rent_n  else 0.0
bill_share  = (electricity_bill / bill_n) if bill_n  else 0.0
maid_due    = maid_per_person * maid_n

total_groceries = df.loc[df["In Groceries"], "Groceries Paid"].sum()
total_water     = df.loc[df["In Water"],     "Water Paid"].sum()
groc_share  = (total_groceries / groc_n)  if groc_n  else 0.0
water_share = (total_water     / water_n) if water_n else 0.0

df["Rent Share"] = df["In Rent"].map(lambda x: rent_share      if x else 0.0)
df["Bill Share"] = df["In Bill"].map(lambda x: bill_share      if x else 0.0)
df["Maid Share"] = df["In Maid"].map(lambda x: maid_per_person if x else 0.0)
df["Total RBM"]  = df["Rent Share"] + df["Bill Share"] + df["Maid Share"]

# Positive Eq = spent MORE than share → reduces what they owe
# Negative Eq = spent LESS than share → increases what they owe
df["Groc Eq"]  = df.apply(lambda r: r["Groceries Paid"] - groc_share  if r["In Groceries"] else 0.0, axis=1)
df["Water Eq"] = df.apply(lambda r: r["Water Paid"]     - water_share if r["In Water"]     else 0.0, axis=1)

# Final Total > 0 → person OWES this amount
# Final Total < 0 → person OVERPAID, should RECEIVE back
df["KW Adjust"]  = df["Groc Eq"] + df["Water Eq"]
df["Final Total"] = (df["Total RBM"] - df["KW Adjust"]).round(2)

# Split Final Total into: how much goes to Maid vs Owner
# Maid portion = Maid Share (fixed per person)
# Owner portion = Rent Share + Bill Share
# But KW adjustment reduces the total — apply adjustment against owner portion first
df["To Maid"]  = df["Maid Share"].clip(lower=0.0)
df["To Owner"] = (df["Final Total"] - df["To Maid"]).round(2)
# If To Owner < 0, person overpaid groceries/water beyond their maid share
# Cap To Maid at Final Total if Final Total < Maid Share
df["To Maid"]  = df.apply(lambda r: min(r["Maid Share"], r["Final Total"]) if r["Final Total"] >= 0 else 0.0, axis=1)
df["To Owner"] = (df["Final Total"] - df["To Maid"]).round(2)

st.divider()
st.subheader("3. Results")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Per-head Grocery",  f"₹{groc_share:,.2f}")
m2.metric("Per-head Water",    f"₹{water_share:,.2f}")
m3.metric("Maid Total Due",    f"₹{maid_due:,.2f}")
m4.metric("Owner Due",         f"₹{owner_due:,.2f}")
m5.metric("Electricity Bill",  f"₹{electricity_bill:,.2f}")

display_cols = ["Name", "Rent Share", "Bill Share", "Maid Share", "Total RBM",
                "Groceries Paid", "Water Paid", "Groc Eq", "Water Eq",
                "KW Adjust", "Final Total", "To Maid", "To Owner"]
styled_df = df[display_cols].round(2)


def color_cell(val):
    if val < -0.005:
        return "background-color:#d4edda"
    if val > 0.005:
        return "background-color:#f8d7da"
    return ""


st.dataframe(
    styled_df.style.format(precision=2)
             .map(color_cell, subset=["Final Total", "To Owner"]),
    use_container_width=True, hide_index=True,
)
st.caption("🟢 Green = overpaid (receive back) | 🔴 Red = still owes")

st.markdown("**Per-person summary:**")
for _, row in df.iterrows():
    ft = row["Final Total"]
    tm = row["To Maid"]
    to = row["To Owner"]
    if ft > 0.01:
        parts = []
        if tm > 0.01:  parts.append(f"₹{tm:,.2f} → Maid")
        if to > 0.01:  parts.append(f"₹{to:,.2f} → Owner")
        if to < -0.01: parts.append(f"Owner owes them ₹{-to:,.2f} back")
        st.write(f"• **{row['Name']}** pays ₹{ft:,.2f}  ({' + '.join(parts)})")
    elif ft < -0.01:
        st.write(f"• **{row['Name']}** should receive ₹{-ft:,.2f} back from Owner")
    else:
        st.write(f"• **{row['Name']}** is settled ✅")

# =================================================================
# 5. Settlement
# =================================================================
st.divider()
st.subheader("4. Settlement")

# People who owe money (Final Total > 0)
payers    = df[df["Final Total"] >  0.005][["Name", "Final Total", "To Maid", "To Owner"]].reset_index(drop=True)
# People who overpaid groceries/water and should receive money back
receivers = df[df["Final Total"] < -0.005][["Name", "Final Total"]].reset_index(drop=True)
total_refunds = round(-receivers["Final Total"].sum(), 2) if not receivers.empty else 0.0

# Safe empty frame so Excel save never crashes
settle_rows = pd.DataFrame(columns=["Name", "Owes ₹", "Pay to Maid ₹", "Pay to Owner ₹"])


def best_subset(amounts, target):
    """Return list of indices (0-based) whose sum >= target with minimum excess."""
    n = len(amounts)
    if n == 0 or target <= 0:
        return []
    best_combo, best_excess = None, None
    for r in range(1, n + 1):
        for combo in itertools.combinations(range(n), r):
            s = sum(amounts[i] for i in combo)
            if s >= target - 1e-6:
                excess = s - target
                if best_excess is None or excess < best_excess:
                    best_excess, best_combo = excess, combo
    return list(best_combo) if best_combo is not None else list(range(n))


if payers.empty:
    st.warning("No one owes money — nothing to settle.")
else:
    amounts = payers["Final Total"].tolist()
    names   = payers["Name"].tolist()

    # ── Step 1: find best combo for MAID (priority first) ──────────
    maid_idx  = best_subset(amounts, maid_due)
    maid_sum  = round(sum(amounts[i] for i in maid_idx), 2)
    maid_extra = round(maid_sum - maid_due, 2)   # extra collected beyond maid_due

    # ── Step 2: assign pay_maid / pay_owner per person ─────────────
    # For the maid group: if one person causes excess, split that person
    # For owner group: full amount goes to owner
    pay_maid  = {n: 0.0 for n in names}
    pay_owner = {n: 0.0 for n in names}

    if maid_extra <= 0.005:
        # Exact or under — all maid-group pays full to maid
        for i in maid_idx:
            pay_maid[names[i]] = amounts[i]
    else:
        # Excess exists — fill maid_due exactly, split the last person
        # Sort maid group smallest first so we fill with smaller amounts first
        sorted_maid = sorted(maid_idx, key=lambda i: amounts[i])
        running = 0.0
        for i in sorted_maid:
            remaining_needed = round(maid_due - running, 2)
            if amounts[i] <= remaining_needed + 0.005:
                pay_maid[names[i]] = amounts[i]
                running = round(running + amounts[i], 2)
            else:
                # This person is split: exactly what's needed → Maid, rest → Owner
                pay_maid[names[i]]  = remaining_needed
                pay_owner[names[i]] = round(amounts[i] - remaining_needed, 2)
                running = maid_due

    # Everyone NOT in maid group pays full to owner
    maid_set = set(maid_idx)
    for i, n in enumerate(names):
        if i not in maid_set:
            pay_owner[n] = amounts[i]

    # ── Step 3: build default settlement table ──────────────────────
    settle_rows = pd.DataFrame([
        {
            "Name":           n,
            "Owes ₹":         round(amounts[i], 2),
            "Pay to Maid ₹":  round(pay_maid[n], 2),
            "Pay to Owner ₹": round(pay_owner[n], 2),
        }
        for i, n in enumerate(names)
    ])

    # ── Step 4: show auto-calculated result ────────────────────────
    st.caption(
        f"Auto-calculated: best combination to cover Maid ₹{maid_due:,.2f} first, "
        f"remainder to Owner ₹{owner_due:,.2f}. "
        "Override using the dropdowns below if needed."
    )
    st.dataframe(settle_rows, hide_index=True, use_container_width=True)

    auto_maid_total  = round(settle_rows["Pay to Maid ₹"].sum(), 2)
    auto_owner_total = round(settle_rows["Pay to Owner ₹"].sum(), 2)
    net_owner        = round(auto_owner_total + (auto_maid_total - maid_due) - total_refunds, 2)

    r1, r2, r3 = st.columns(3)
    r1.metric("Collected for Maid",  f"₹{auto_maid_total:,.2f}",
              delta=f"{'exact' if abs(auto_maid_total-maid_due)<0.01 else f'extra ₹{auto_maid_total-maid_due:,.2f}'}")
    r2.metric("Collected for Owner", f"₹{auto_owner_total:,.2f}")
    r3.metric("Net Owner receives",  f"₹{net_owner:,.2f}",
              delta=f"target ₹{owner_due:,.2f}")

    # ── Step 5: optional manual override per person ─────────────────
    st.divider()
    st.markdown("**Override (optional) — change where a person sends their money:**")
    st.caption("Default is pre-filled from auto-calculation. Only change if needed.")

    override_rows = []
    for i, row in settle_rows.iterrows():
        n   = row["Name"]
        ft  = row["Owes ₹"]
        col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
        col1.markdown(f"**{n}** — owes ₹{ft:,.2f}")
        dest = col4.selectbox(
            "Send to", options=["— auto —", "Maid", "Owner", "Split (Maid+Owner)"],
            index=0, key=f"dest_{n}", label_visibility="collapsed"
        )
        if dest == "— auto —":
            pm = row["Pay to Maid ₹"]
            po = row["Pay to Owner ₹"]
        elif dest == "Maid":
            pm, po = ft, 0.0
        elif dest == "Owner":
            pm, po = 0.0, ft
        else:  # Split
            pm = round(df.loc[df["Name"] == n, "To Maid"].values[0], 2)
            po = round(ft - pm, 2)
        col2.markdown(f"Maid: **₹{pm:,.2f}**")
        col3.markdown(f"Owner: **₹{po:,.2f}**")
        override_rows.append({"Name": n, "Owes ₹": ft,
                               "Pay to Maid ₹": pm, "Pay to Owner ₹": po})

    final_settle = pd.DataFrame(override_rows)
    final_maid   = round(final_settle["Pay to Maid ₹"].sum(), 2)
    final_owner  = round(final_settle["Pay to Owner ₹"].sum(), 2)
    final_net    = round(final_owner + (final_maid - maid_due) - total_refunds, 2)

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**➡️ Pay to Maid**")
        maid_payers = final_settle[final_settle["Pay to Maid ₹"] > 0.005][["Name", "Pay to Maid ₹"]]
        if not maid_payers.empty:
            st.dataframe(maid_payers, hide_index=True, use_container_width=True)
        diff = final_maid - maid_due
        if abs(diff) < 0.01:
            st.success(f"₹{final_maid:,.2f} — exact ✅")
        elif diff > 0:
            st.warning(f"₹{final_maid:,.2f} — ₹{diff:,.2f} extra → forward to Owner")
        else:
            st.error(f"₹{final_maid:,.2f} — short ₹{-diff:,.2f}")

    with col_b:
        st.markdown("**➡️ Pay to Owner**")
        owner_payers = final_settle[final_settle["Pay to Owner ₹"] > 0.005][["Name", "Pay to Owner ₹"]]
        if not owner_payers.empty:
            st.dataframe(owner_payers, hide_index=True, use_container_width=True)
        st.write(f"Collected: ₹{final_owner:,.2f}")
        if abs(final_maid - maid_due) > 0.01:
            st.write(f"+ Maid excess: ₹{final_maid - maid_due:,.2f}")
        if total_refunds > 0:
            st.write(f"− Owner refunds: ₹{total_refunds:,.2f}")
        if abs(final_net - owner_due) < 0.05:
            st.success(f"Net Owner receives: ₹{final_net:,.2f} ✅")
        else:
            st.warning(f"Net Owner receives: ₹{final_net:,.2f} (target ₹{owner_due:,.2f})")

    if not receivers.empty:
        st.markdown("**⬅️ Owner refunds these people (overpaid Groceries/Water):**")
        st.dataframe(
            receivers.assign(**{"Refund ₹": (-receivers["Final Total"]).round(2)})[["Name", "Refund ₹"]],
            hide_index=True, use_container_width=True,
        )

st.divider()

# =================================================================
# 6. Save / Export to Excel
# =================================================================
st.subheader("5. Save to Excel")

col_m, col_y, col_btn = st.columns([2, 1, 1])
with col_m:
    sel_month = st.selectbox("Month", MONTHS, index=datetime.date.today().month - 1)
with col_y:
    sel_year = st.selectbox("Year", list(range(2023, 2031)),
                            index=datetime.date.today().year - 2023)

filename = f"Room_Expense_{sel_month}_{sel_year}.xlsx"
filepath = os.path.join(DATA_DIR, filename)

with col_btn:
    st.write("")
    st.write("")
    save_clicked = st.button("💾 Save / Override Excel", use_container_width=True)

if save_clicked:
    existed = os.path.exists(filepath)
    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        styled_df.to_excel(writer, sheet_name="Summary", index=False)

        if not settle_rows.empty:
            final_settle.round(2).to_excel(writer, sheet_name="Settlement", index=False)
        if not receivers.empty:
            receivers.assign(**{"Refund Amount": -receivers["Final Total"]}) \
                     [["Name", "Refund Amount"]].round(2) \
                     .to_excel(writer, sheet_name="Settlement-Refunds", index=False)

        df[["Name", "In Rent", "In Bill", "In Maid", "In Groceries", "In Water",
            "Groceries Paid", "Water Paid"]].to_excel(writer, sheet_name="Inputs", index=False)

        pd.DataFrame({
            "Setting": ["Total Rent", "Prev Unit", "Curr Unit", "Units Used",
                        "Rate per Unit", "Electricity Bill", "Maid per Person",
                        "Maid Total Due", "Owner Total Due (Rent+Bill)"],
            "Value":   [total_rent, prev_unit, curr_unit, units_used,
                        rate_per_unit, electricity_bill, maid_per_person,
                        maid_due, owner_due],
        }).to_excel(writer, sheet_name="Settings", index=False)

    st.success(("Overridden: " if existed else "Saved: ") + filename)

if os.path.exists(filepath):
    with open(filepath, "rb") as f:
        st.download_button(
            "⬇️ Download Excel", data=f.read(),
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
