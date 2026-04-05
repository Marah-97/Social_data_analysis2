import json
from pathlib import Path

import numpy as np
import pandas as pd

HIST_FILE = Path('Police_Department_Incident_Reports__Historical_2003_to_May_2018_20260224.csv')
NEW_FILE = Path('Police_Department_Incident_Reports__2018_to_Present_20260224.csv')
OUT_HTML = Path('fig3_policy_shift.html')
MIN_YEAR = 2003
MAX_YEAR = 2025

GROUP_ORDER = [
    'Possession/Paraphernalia',
    'Sales/Distribution',
    'Use/Under influence',
    'Loitering/Place',
    'Other legal subtype',
]

LEGEND_LABELS = {
    'Possession/Paraphernalia': 'Possession',
    'Sales/Distribution': 'Sales',
    'Use/Under influence': 'Use',
    'Loitering/Place': 'Loitering',
    'Other legal subtype': 'Other',
}

# Load and standardize historical file.
h = pd.read_csv(
    HIST_FILE,
    usecols=['Date', 'Category', 'Descript', 'Incident Code'],
)
h['year'] = pd.to_datetime(h['Date'], errors='coerce').dt.year
h['cat'] = h['Category'].astype(str).str.upper()
h['desc'] = h['Descript'].astype(str).str.upper()

# Load and standardize 2018+ file.
n = pd.read_csv(
    NEW_FILE,
    usecols=['Incident Date', 'Incident Category', 'Incident Description', 'Incident Code'],
)
n['year'] = pd.to_datetime(n['Incident Date'], errors='coerce').dt.year
n['cat'] = n['Incident Category'].astype(str).str.upper()
n['desc'] = n['Incident Description'].astype(str).str.upper()

# Keep only drug-related incidents.
h_drug = h[h['cat'].str.contains('DRUG', na=False)][['year', 'desc', 'Incident Code']].copy()
n_drug = n[n['cat'].str.contains('DRUG', na=False)][['year', 'desc', 'Incident Code']].copy()

h_drug = h_drug.rename(columns={'Incident Code': 'code'})
n_drug = n_drug.rename(columns={'Incident Code': 'code'})

df = pd.concat([h_drug, n_drug], ignore_index=True)
df = df[df['year'].between(MIN_YEAR, MAX_YEAR)].copy()

# Group legal event types based on incident descriptions.
s = df['desc']
df['group'] = np.select(
    [
        s.str.contains('SALE|SALES|TRANSPORT', na=False),
        s.str.contains('UNDER THE INFLUENCE|USE', na=False),
        s.str.contains('LOITERING|MAINTAINING PREMISE', na=False),
        s.str.contains('POSSESSION|PARAPHERNALIA', na=False),
    ],
    [
        'Sales/Distribution',
        'Use/Under influence',
        'Loitering/Place',
        'Possession/Paraphernalia',
    ],
    default='Other legal subtype',
)

count_pt = (
    df.groupby(['year', 'group'])
      .size()
      .unstack(fill_value=0)
      .reindex(columns=GROUP_ORDER, fill_value=0)
      .sort_index()
)

share_pt = count_pt.div(count_pt.sum(axis=1), axis=0) * 100

groups = count_pt.columns.tolist()
compare_years = [2024, 2025]
counts_2024 = count_pt.loc[2024, groups]
counts_2025 = count_pt.loc[2025, groups]
share_2024_by_group = share_pt.loc[2024, groups].round(3)
share_2025_by_group = share_pt.loc[2025, groups].round(3)
delta_by_group = (counts_2025 - counts_2024)
delta_sorted = delta_by_group.sort_values(ascending=False)

# Useful summary values for text.
code_16710_share = (
    df.assign(is_16710=df['code'].astype(str).eq('16710'))
      .groupby('year')['is_16710']
      .mean()
      .mul(100)
      .round(1)
)

share_2014 = code_16710_share.get(2014, float('nan'))
share_2024 = code_16710_share.get(2024, float('nan'))
share_2025 = code_16710_share.get(2025, float('nan'))

totals = count_pt.sum(axis=1)
tot_2014 = int(totals.get(2014, 0))
tot_2024 = int(totals.get(2024, 0))
tot_2025 = int(totals.get(2025, 0))
tot_delta = tot_2025 - tot_2024

palette = {
    'Possession/Paraphernalia': '#C0392B',
    'Sales/Distribution': '#1A7A6E',
    'Use/Under influence': '#B8860B',
    'Loitering/Place': '#7F8C8D',
    'Other legal subtype': '#5D6D7E',
}
colors = [palette[g] for g in groups]

delta_labels = [LEGEND_LABELS[g] for g in delta_sorted.index]
delta_values = [int(v) for v in delta_sorted.values]
delta_colors = ['#1A7A6E' if v >= 0 else '#C0392B' for v in delta_values]
stack_2024 = [float(share_2024_by_group[g]) for g in groups]
stack_2025 = [float(share_2025_by_group[g]) for g in groups]

html_template = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Figure 3: Policy-sensitive drug incident mix</title>
  <script src=\"https://cdn.plot.ly/plotly-2.35.2.min.js\"></script>
  <style>
    html, body { margin: 0; padding: 0; background: #ffffff; }
    #chart { width: 100%; height: 760px; }
  </style>
</head>
<body>
  <div id=\"chart\"></div>
  <script>
    const groups = __GROUPS__;
    const labels = __LEGEND_LABELS__;
    const colors = __COLORS__;
    const compareYears = __COMPARE_YEARS__;
    const deltaLabels = __DELTA_LABELS__;
    const deltaValues = __DELTA_VALUES__;
    const deltaColors = __DELTA_COLORS__;
    const stack2024 = __STACK_2024__;
    const stack2025 = __STACK_2025__;

    const traces = [{
      type: 'bar',
      x: deltaLabels,
      y: deltaValues,
      marker: { color: deltaColors },
      text: deltaValues.map(v => `${v >= 0 ? '+' : ''}${v.toLocaleString()}`),
      textposition: 'auto',
      cliponaxis: false,
      showlegend: false,
      hovertemplate: '%{x}<br>Change=%{y:+,.0f}<extra></extra>',
      xaxis: 'x',
      yaxis: 'y'
    }];

    groups.forEach((grp, i) => {
      traces.push({
        type: 'bar',
        x: compareYears,
        y: [stack2024[i], stack2025[i]],
        name: labels[grp] || grp,
        marker: { color: colors[i] },
        hovertemplate: '%{fullData.name}<br>Year=%{x}<br>Share=%{y:.1f}%<extra></extra>',
        xaxis: 'x2',
        yaxis: 'y2'
      });
    });

    const layout = {
      title: {
        text: 'What drove the 2025 rebound in drug incidents?',
        x: 0.01, xanchor: 'left',
        y: 0.98
      },
      paper_bgcolor: '#ffffff',
      plot_bgcolor: '#ffffff',
      barmode: 'stack',
      margin: { l: 108, r: 78, t: 110, b: 170 },
      legend: {
        orientation: 'h',
        y: -0.22, x: 0.0,
        yanchor: 'top', xanchor: 'left',
        entrywidth: 92,
        entrywidthmode: 'pixels',
        font: {size: 12},
        bgcolor: 'rgba(255,255,255,0.0)'
      },
      xaxis: {
        domain: [0.0, 1.0],
        tickangle: -18,
        categoryorder: 'array',
        categoryarray: deltaLabels,
        showgrid: false
      },
      yaxis: {
        domain: [0.58, 1.0],
        title: 'Change in incidents (2025 - 2024)',
        zeroline: true,
        zerolinecolor: '#999999',
        zerolinewidth: 1.2,
        showgrid: true, gridcolor: '#ECECEC'
      },
      xaxis2: {
        domain: [0.0, 1.0],
        anchor: 'y2',
        title: 'Year',
        type: 'category',
        showgrid: false
      },
      yaxis2: {
        domain: [0.0, 0.42],
        anchor: 'x2',
        title: 'Share of annual incidents (%)',
        range: [0, 100],
        showgrid: true, gridcolor: '#ECECEC'
      },
      annotations: [
        {
          xref: 'paper', yref: 'paper',
          x: 0.06, y: 1.08, xanchor: 'left',
          text: 'Net change by subtype (2025 vs 2024)',
          showarrow: false, font: { size: 13, color: '#333333' }
        },
        {
          xref: 'paper', yref: 'paper',
          x: 0.01, y: 0.48, xanchor: 'left',
          text: 'Composition shift between years',
          showarrow: false, font: { size: 13, color: '#333333' }
        },
        {
          xref: 'paper', yref: 'paper',
          x: 0.965, y: 1.08, xanchor: 'right',
          text: '<b>Total change:</b> __TOTAL_DELTA__',
          showarrow: false, font: { size: 12, color: '#333333' }
        }
      ]
    };

    Plotly.newPlot('chart', traces, layout, { responsive: true, displayModeBar: false });
  </script>
</body>
</html>
"""

html = (
    html_template
    .replace('__GROUPS__', json.dumps(groups))
    .replace('__LEGEND_LABELS__', json.dumps(LEGEND_LABELS))
    .replace('__COLORS__', json.dumps(colors))
    .replace('__COMPARE_YEARS__', json.dumps([str(y) for y in compare_years]))
    .replace('__DELTA_LABELS__', json.dumps(delta_labels))
    .replace('__DELTA_VALUES__', json.dumps(delta_values))
    .replace('__DELTA_COLORS__', json.dumps(delta_colors))
    .replace('__STACK_2024__', json.dumps(stack_2024))
    .replace('__STACK_2025__', json.dumps(stack_2025))
    .replace('__TOTAL_DELTA__', f'{tot_delta:+,}')
)

OUT_HTML.write_text(html, encoding='utf-8')

print(f'Wrote {OUT_HTML}')
print(f'Totals: 2014={tot_2014}, 2024={tot_2024}, 2025={tot_2025}')
print(f'Delta 2025-2024 by group: {delta_sorted.to_dict()}')
print(f'Code 16710 share (%): 2014={share_2014}, 2024={share_2024}, 2025={share_2025}')
