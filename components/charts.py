import pandas as pd
import plotly.graph_objects as go

from translations import t

_PURGE_COLOUR = "orange"
_MEAN_COLOUR = "red"
_MEDIAN_COLOUR = "green"


def plot_ach_distribution(results_df: pd.DataFrame, params, lang: str) -> go.Figure:
    """Histogram of all ACH values with mean, median, and purge threshold lines."""
    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=results_df["ACH_per_hour"],
        nbinsx=30,
        marker_color="steelblue",
        opacity=0.8,
        name=t("ach_label", lang),
    ))

    mean_val = results_df["ACH_per_hour"].mean()
    median_val = results_df["ACH_per_hour"].median()

    for val, colour, label in [
        (mean_val,              _MEAN_COLOUR,   f'{t("mean", lang)}: {mean_val:.3f}'),
        (median_val,            _MEDIAN_COLOUR, f'{t("median", lang)}: {median_val:.3f}'),
        (params.max_ach_normal, _PURGE_COLOUR,  f'{t("purge_threshold", lang)}: {params.max_ach_normal}'),
    ]:
        fig.add_vline(x=val, line_dash="dash", line_color=colour, annotation_text=label,
                      annotation_position="top right")

    fig.update_layout(
        xaxis_title=t("ach_label", lang),
        yaxis_title=t("frequency", lang),
        showlegend=False,
        margin=dict(t=20, b=40),
    )
    return fig


def plot_ach_by_building(results_df: pd.DataFrame, params, lang: str) -> go.Figure:
    """Box plot per building, sorted by median ACH."""
    order = (
        results_df.groupby("HouseNo")["ACH_per_hour"]
        .median()
        .sort_values()
        .index.tolist()
    )

    fig = go.Figure()
    for house in order:
        vals = results_df[results_df["HouseNo"] == house]["ACH_per_hour"]
        fig.add_trace(go.Box(
            y=vals,
            name=house,
            marker_color="steelblue",
            boxmean=True,
        ))

    fig.add_hline(
        y=params.max_ach_normal,
        line_dash="dot",
        line_color=_PURGE_COLOUR,
        annotation_text=t("purge_threshold", lang),
        annotation_position="top left",
    )

    fig.update_layout(
        yaxis_title=t("ach_label", lang),
        showlegend=False,
        margin=dict(t=20, b=40),
    )
    return fig


def plot_co2_timeline(
    df: pd.DataFrame,
    house: str,
    results_df: pd.DataFrame,
    lang: str,
) -> go.Figure:
    """
    Raw CO2 over time for one building.
    Accepted decay start points are marked with vertical lines.
    """
    house_df = df[df["HouseNo"] == house].sort_values("DateTime")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=house_df["DateTime"],
        y=house_df["CO2_ppm"],
        mode="lines",
        line=dict(color="steelblue", width=1),
        name=t("co2_ppm", lang),
    ))

    # Mark accepted decay start times
    house_results = results_df[results_df["HouseNo"] == house]
    if not house_results.empty:
        decay_starts = pd.to_datetime(house_results["C0_timestamp"], utc=True)
        decay_co2 = []
        for ts in decay_starts:
            idx = (house_df["DateTime"] - ts).abs().idxmin()
            decay_co2.append(house_df.loc[idx, "CO2_ppm"])

        fig.add_trace(go.Scatter(
            x=decay_starts,
            y=decay_co2,
            mode="markers",
            marker=dict(color=_MEAN_COLOUR, size=8, symbol="triangle-down"),
            name=t("accepted", lang),
        ))

    fig.add_hline(
        y=420,
        line_dash="dot",
        line_color="grey",
        annotation_text="420 ppm",
        annotation_position="bottom right",
    )

    fig.update_layout(
        xaxis_title=None,
        yaxis_title=t("co2_ppm", lang),
        showlegend=True,
        legend=dict(orientation="h", y=1.02, x=0),
        margin=dict(t=30, b=40),
    )
    return fig


def plot_ach_vs_decay_rate(results_df: pd.DataFrame, params, lang: str) -> go.Figure:
    """Scatter of ACH vs initial decay rate, coloured by R²."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=results_df["ACH_per_hour"],
        y=results_df["InitialDecayRate_ppm_h"],
        mode="markers",
        marker=dict(
            color=results_df["R_squared"],
            colorscale="Viridis",
            cmin=params.min_r_squared,
            cmax=1.0,
            size=10,
            opacity=0.8,
            line=dict(width=0.5, color="black"),
            colorbar=dict(title=t("r_squared", lang)),
        ),
        text=[
            f"{row['HouseNo']}<br>ACH={row['ACH_per_hour']:.3f}<br>R²={row['R_squared']:.3f}"
            for _, row in results_df.iterrows()
        ],
        hoverinfo="text",
    ))

    fig.add_vline(
        x=params.max_ach_normal,
        line_dash="dot",
        line_color=_PURGE_COLOUR,
        annotation_text=f'ACH {params.max_ach_normal}',
        annotation_position="top right",
    )
    fig.add_hline(
        y=params.max_decay_rate,
        line_dash="dot",
        line_color="purple",
        annotation_text=f'{params.max_decay_rate} ppm/h',
        annotation_position="top left",
    )

    fig.update_layout(
        xaxis_title=t("ach_label", lang),
        yaxis_title=t("initial_decay_rate", lang),
        showlegend=False,
        margin=dict(t=20, b=40),
    )
    return fig
