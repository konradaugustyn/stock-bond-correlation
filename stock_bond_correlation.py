import pandas as pd
import matplotlib.pyplot as plt

# import data
df = pd.read_excel(
    "ie_data.xls",
    sheet_name="Data",
    skiprows=8,
    index_col=0,
    header=None,
    usecols="A,E,J,S",
    names=["date", "cpi", "stock_real", "bond_real"],
    skipfooter=1,
)
df.index = pd.to_datetime(df.index.map(lambda x: f"{float(x):.2f}"), format="%Y.%m")

# nominal returns
nominal_stock_return = (df["stock_real"] / df["stock_real"].shift(1)) * (
    df["cpi"] / df["cpi"].shift(1)
) - 1
nominal_bond_return = (df["bond_real"] / df["bond_real"].shift(1)) * (
    df["cpi"] / df["cpi"].shift(1)
) - 1

# 24-month rolling window
rolling_correlation = nominal_stock_return.rolling(24).corr(nominal_bond_return)

inflation_yoy = df["cpi"] / df["cpi"].shift(12) - 1

df["rolling_correlation"] = rolling_correlation
df["inflation_yoy"] = inflation_yoy

# analysis time period
analysis = df.loc["1970.01":"2026.06"].copy()

# plot
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
analysis["rolling_correlation"].plot(ax=ax1, title="24-month stock-bond correlation")
ax1.axhline(0, color="gray", linewidth=1)
(analysis["inflation_yoy"] * 100).plot(ax=ax2, ylabel="annual inflation (%)")
plt.tight_layout()
plt.savefig("24-month_stock-bond_correlation.png")

# 60 / 40 portfolio
portfolio_return = 0.6 * nominal_stock_return + 0.4 * nominal_bond_return
analysis["portfolio_return"] = portfolio_return
wealth = 100
analysis["portfolio_wealth"] = wealth * (analysis["portfolio_return"] + 1).cumprod()

# drawdown
analysis["current_peak"] = analysis["portfolio_wealth"].cummax().clip(lower=100)
analysis["drawdown"] = analysis["portfolio_wealth"] / analysis["current_peak"] - 1

# monthly inflation
inflation_monthly = df["cpi"] / df["cpi"].shift(1) - 1
analysis["inflation_monthly"] = inflation_monthly

analysis["portfolio_real_return"] = (1 + analysis["portfolio_return"]) / (
    1 + analysis["inflation_monthly"]
) - 1
analysis["portfolio_real_wealth"] = (
    1 + analysis["portfolio_real_return"]
).cumprod() * 100
analysis["current_real_peak"] = (
    analysis["portfolio_real_wealth"].cummax().clip(lower=100)
)
analysis["real_drawdown"] = (
    analysis["portfolio_real_wealth"] / analysis["current_real_peak"] - 1
)

corr_regime = rolling_correlation.mask(rolling_correlation > 0, other="positive").mask(
    rolling_correlation < 0, other="negative"
)
analysis["corr_regime"] = corr_regime

reg_drawdown = analysis.groupby("corr_regime")["drawdown"].min()
reg_real_drawdown = analysis.groupby("corr_regime")["real_drawdown"].min()
reg_av_an_infl = analysis.groupby("corr_regime")["inflation_yoy"].mean()
reg_months = analysis.groupby("corr_regime").size()

summary = pd.DataFrame(
    {
        "Months": reg_months,
        "Average annual inflation (%)": reg_av_an_infl * 100,
        "Max nominal drawdown (%)": reg_drawdown * 100,
        "Max real drawdown (%)": reg_real_drawdown * 100,
    }
)
summary.to_csv("regime_summary.csv")


def total_return(returns, start, end):
    ret = (1 + returns.loc[start:end]).prod() - 1
    return ret


sign_flip = [
    ("1973-74", "1973-02", "1974-09"),
    ("2000-03", "2000-09", "2003-02"),
    ("2007-09", "2007-11", "2009-03"),
    ("2022", "2022-01", "2022-10"),
]

rows = []
for name, start, end in sign_flip:
    stocks = total_return(nominal_stock_return, start, end)
    bonds = total_return(nominal_bond_return, start, end)
    portfolio = total_return(analysis["portfolio_return"], start, end)
    rows.append(
        {
            "Drawdown": name,
            "Stocks (%)": stocks * 100,
            "Bonds (%)": bonds * 100,
            "60/40 (%)": portfolio * 100,
            "60/40 loss / stock loss (%)": portfolio / stocks * 100,
        }
    )

pd.DataFrame(rows).to_csv("drawdown_breakdown.csv", index=False)


# plot
fig_dd, ax_dd = plt.subplots()
ax_dd.plot(analysis.index, (analysis["drawdown"] * 100), label="Nominal")
ax_dd.plot(analysis.index, (analysis["real_drawdown"] * 100), label="Real")
plt.title("60/40 portfolio drawdowns")
plt.ylabel("Drawdown (%)")
ax_dd.fill_between(
    x=analysis.index,
    y1=0,
    y2=1,
    where=analysis["corr_regime"] == "positive",
    transform=ax_dd.get_xaxis_transform(),
    color="gray",
    alpha=0.15,
    label="Positive correlation",
)
plt.legend()
plt.tight_layout()
plt.savefig("60_40_portfolio_drawdowns.png")
