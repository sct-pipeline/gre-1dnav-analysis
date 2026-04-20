#!/usr/bin/env python3

import argparse
import matplotlib.pyplot as plt
import os
import pandas as pd
from scipy import stats


def create_ghosting_figure(fname_csv, path_output):
    # Subject-ID/Session-ID/Acquisition  max rec-standard  max rec-navigated  mean rec-standard  mean rec-navigated
    df = pd.read_csv(fname_csv)
    df_uppert = df[df['Subject-ID/Session-ID/Acquisition'].str.contains('upperT')]
    df_lowert = df[df['Subject-ID/Session-ID/Acquisition'].str.contains('lowerT')]
    df_lse = df[df['Subject-ID/Session-ID/Acquisition'].str.contains('LSE')]

    fig = plt.figure(figsize=(6, 5))
    x_ticks = [1, 1.5, 2, 2.5]
    x_offset = 0.05
    ax = fig.subplots(1,1)

    data_standard = [df_uppert['mean rec-standard'], df_lowert['mean rec-standard'], df_lse['mean rec-standard'], df['mean rec-standard']]
    data_navigated = [df_uppert['mean rec-navigated'], df_lowert['mean rec-navigated'], df_lse['mean rec-navigated'], df['mean rec-navigated']]

    # Perform independent t-test
    t_statistics = []
    p_values = []
    for i in range(len(data_standard)):
        t, p = stats.ttest_ind(data_navigated[i], data_standard[i], equal_var=False, alternative='less')
        t_statistics.append(t)
        p_values.append(p)

    vp1 = ax.violinplot(data_standard, positions=x_ticks, side='low', showmeans=False, showmedians=False, showextrema=False)
    vp2 = ax.violinplot(data_navigated, positions=x_ticks, side='high', showmeans=False, showmedians=False, showextrema=False)

    ax.boxplot(data_standard, positions=[x - x_offset for x in x_ticks], widths=0.06, patch_artist=True, boxprops=dict(facecolor='white', color='black', alpha=0.5), medianprops=dict(color='black'), showfliers=False, showcaps=False, whis=0)
    ax.boxplot(data_navigated, positions=[x + x_offset for x in x_ticks], widths=0.06, patch_artist=True,
                  boxprops=dict(facecolor='white', color='black', alpha=0.5), medianprops=dict(color='black'),
                  showfliers=False, showcaps=False, whis=0)

    for i in range(len(x_ticks)):
        color_standard = '#1a80bb'  # Blue color for standard
        color_navigated = '#ea801c'  # Orange color for navigated
        vp1['bodies'][i].set_facecolor(color_standard)
        vp2['bodies'][i].set_facecolor(color_navigated)
        if i == len(x_ticks) - 1:
            vp1['bodies'][i].set_alpha(0.8)
            vp2['bodies'][i].set_alpha(0.8)
        else:
            vp1['bodies'][i].set_alpha(0.5)
            vp2['bodies'][i].set_alpha(0.5)
    ax.grid(linestyle='--', alpha=0.5)
    ax.xaxis.grid(False)
    ax.set_title('Mean ghost signal intensity for each subject')
    ax.set_ylabel('Ghost signal intensity')
    ax.set_xticks([1, 1.5, 2, 2.5])  # Set x-axis ticks for each violin
    ax.set_xticklabels(['Upper thor.', 'Lower thor.', 'Lumbar', 'All regions'])  # Set x-axis labels
    ax.set_xlim(min(x_ticks) - 0.35, max(x_ticks) + 0.35)
    ax.set_ylim(-50, 1200)
    # Add stars and whiskers
    for i in range(len(x_ticks)):
        star_text = p_value_to_stars(p_values[i])
        if i == 0:
            y_tick = 900
        else:
            y_tick = 1000
        if star_text:
            ax.text(x_ticks[i], y_tick, star_text, ha='center', va='bottom', fontsize=10)
            # Add whiskers
            ax.errorbar(x_ticks[i], y_tick, xerr=0.075, color='black', linewidth=1, barsabove=True, capsize=5)

    legend_handles = [vp1["bodies"][3], vp2["bodies"][3]]
    legend_labels = ['Default', 'Navigated']
    ax.legend(legend_handles, legend_labels, title='Reconstruction', loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(path_output, 'fig_ghost_vp.png'))
    print(f"T-statistic: {t_statistics}")
    print(f"P-value: {p_values}")


def p_value_to_stars(p):
    # Symbol Meaning
    # ns P > 0.05
    # * P ≤ 0.05
    # ** P ≤ 0.01
    # *** P ≤ 0.001
    # **** P ≤ 0.0001

    if p > 0.05:
        return ''
    elif p <= 0.0001:
        return '****'
    elif p <= 0.001:
        return '***'
    elif p <= 0.01:
        return '**'
    elif p <= 0.05:
        return '*'


def main():
    parser = argparse.ArgumentParser(
        description=f"Generate the figures."
    )
    # parser.add_argument("path_data", help="Path to the data directory.", default=None)
    parser.add_argument("path_processed_data", nargs='?', default=None,
                        help="Path to the processed data directory (output path). Defaults to path_data if not provided.")
    args = parser.parse_args()
    if not os.path.isdir(args.path_processed_data):
        raise OSError(f"Error: path_processed_data does not exists. Provided path: {args.path_processed_data}")

    path_figures = os.path.join(args.path_processed_data, 'figures')
    if not os.path.exists(path_figures):
        os.makedirs(path_figures)

    fname_ghosting_metrics = os.path.join(args.path_processed_data, 'results', 'ghosting_metrics.csv')
    create_ghosting_figure(fname_ghosting_metrics, path_figures)


if __name__ == "__main__":
    main()
