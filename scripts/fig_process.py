"""Process metrics from the archived HK aggregates, with explicit denominators.

Preserves the published parser's definitions and archived counts; no model calls.
"""
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from data_figure_style import setup,save,panel,clean_axis,WIDTH,MM,INK,MUTED,MULTI,SINGLE,GRID,VOTE,SINGLE_LIGHT
setup()
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'manuscript/figures/process_hk.pdf'
DATA=ROOT/'phase1_evaluation/eval_results/objective_hk/objective_metrics.json'


def main():
    metrics=json.loads(DATA.read_text());native=metrics['paradigm_hk/native_python_HK'];fc=metrics['paradigm_hk/function_calling_HK']
    assert native['runs']==702 and native['n_numerals']==12754
    fig=plt.figure(figsize=(WIDTH,125*MM))
    ax=fig.add_axes([.22,.64,.265,.24]);panel(fig,'a',.025,.96,'Execution reliability')
    for j,(m,col,marker) in enumerate([(native,MULTI,'o'),(fc,SINGLE,'s')]):
        for i,(key,ci) in enumerate([('first_ok_pct','first_ok_ci'),('runs_err_pct','runs_err_ci')]):
            v=m[key];lo,hi=m[ci];y=i+(j-.5)*.22
            ax.errorbar(v,y,xerr=[[v-lo],[hi-v]],fmt=marker,color=col,mfc=col if j==0 else 'white',ms=4,lw=.8,capsize=1.5)
            ax.annotate(f'{v:.1f}',(v,y),xytext=(0,6 if j==0 else -10),textcoords='offset points',ha='center',fontsize=6)
    ax.set(xlim=(-4,105),xticks=[0,50,100],ylim=(1.6,-.6),yticks=[0,1],
           yticklabels=['First-attempt success','Runs with ≥1 error'],xlabel='Runs (%)');clean_axis(ax)
    fig.legend(handles=[Line2D([],[],marker='o',ls='',color=MULTI,label='Native Python / MetaSEQ'),
                        Line2D([],[],marker='s',ls='',mec=SINGLE,mfc='white',label='Function calling (C2)')],
               loc='upper center',bbox_to_anchor=(.54,.57),ncol=2,fontsize=6.5)
    ax=fig.add_axes([.715,.64,.25,.24]);panel(fig,'b',.56,.96,'Errors at the tool interface')
    for i,m in enumerate([native,fc]):
        n=sum(m['taxonomy'].values());k=sum(v for key,v in m['taxonomy'].items() if key.startswith('SQL:'))
        v=100*k/n;ax.barh(i,v,.4,color=MULTI if i==0 else SINGLE,zorder=2)
        ax.text(v+2,i,f'{v:.1f}% ({k}/{n})',va='center',fontsize=6,ha='left')
    ax.set(xlim=(0,135),xticks=[0,50,100],ylim=(1.6,-.6),yticks=[0,1],
           yticklabels=['Native Python','Function calling'],xlabel='Execution errors (%)');clean_axis(ax)
    ax=fig.add_axes([.22,.12,.265,.29]);panel(fig,'c',.025,.48,'Error runs by query category')
    cats=[v for k,v in sorted(metrics.items()) if k.startswith('category_hk/')]
    labels=['Temporal pattern','Geospatial','Multivariate','Urban planning','Decision support','Personal action']
    for i,m in enumerate(cats):
        v=m['runs_err_pct'];ax.barh(i,v,.45,color=MULTI,zorder=2)
        ax.text(v+.13,i,f'{v:.1f}% ({m["n_err_runs"]}/{m["runs"]})',va='center',fontsize=6)
    ax.set(xlim=(0,5.1),xticks=[0,2,4],ylim=(5.6,-.6),yticks=range(6),yticklabels=labels,xlabel='Runs with ≥1 error (%)');clean_axis(ax)
    ax=fig.add_axes([.715,.12,.25,.29]);panel(fig,'d',.56,.48,'Numeral traceability')
    vals=[native['ground_strict_pct'],native['ground_scaled_pct']-native['ground_strict_pct'],100-native['ground_scaled_pct']]
    for i,(v,col) in enumerate(zip(vals,[MULTI,SINGLE_LIGHT,VOTE])):
        ax.barh(i,v,.45,color=col,zorder=2)
        ax.text(v+2,i,f'{v:.1f}%',va='center',fontsize=6.5)
    ax.set(xlim=(0,115),xticks=[0,50,100],ylim=(2.6,-.6),yticks=[0,1,2],
           yticklabels=['Direct trace','Unit conversion only','Untraced'],xlabel='Salient numerals (%)');clean_axis(ax)
    fig.text(.715,.045,'12,754 numerals; traceability is not correctness.',fontsize=5.7,color=MUTED,ha='center')
    save(fig,OUT)


if __name__=='__main__':main()
