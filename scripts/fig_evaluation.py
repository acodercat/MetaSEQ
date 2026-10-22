"""Deployment scores with query-matched judge averages and query-level t intervals.

The category panels share a horizontal model axis and use points rather than
bars with truncated baselines. All scores come from table_deployment.load.
"""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import table_deployment as td
from data_figure_style import setup, save, panel, clean_axis, WIDTH, MM, INK, MUTED, MULTI, SINGLE, VOTE
setup()
OUT=Path(__file__).resolve().parents[1]/'manuscript/figures/evaluation_si.pdf'
COLORS=[SINGLE,MULTI,VOTE]
MARKERS=['o','s','^']
CLASSES=['Spatiotemporal','Multivariate','Management']


def main():
    data={m:td.load(m) for m in td.MODELS}
    models=sorted(td.MODELS,key=lambda m:-np.mean(td.query_scores(data[m])))
    fig=plt.figure(figsize=(WIDTH,155*MM))
    ax=fig.add_axes([.26,.765,.67,.15])
    criteria=['Methodological soundness','Technical implementation','Data integration and synthesis',
              'Response alignment','Faithfulness']
    for offset,color,model,marker in [(-.13,SINGLE,td.BASELINE,'s'),(.13,MULTI,td.PRIMARY,'o')]:
        d=td.load(model)
        for y,c in enumerate(td.CRITERIA):
            mu,hw=td.mean_ci(td.query_scores(d,criterion=c))
            ax.errorbar(mu,y+offset,xerr=hw,fmt=marker,ms=4,mfc='white' if model==td.BASELINE else color,
                        color=color,lw=.8,capsize=1.5)
    ax.set(xlim=(0,1.03),xticks=[0,.25,.5,.75,1],ylim=(4.6,-.6),yticks=range(5),
           yticklabels=criteria,xlabel='Mean judge score')
    clean_axis(ax)
    ax.legend(handles=[Line2D([],[],marker='s',ls='',mfc='white',mec=SINGLE,ms=4,label='Web-search baseline (C1)'),
                       Line2D([],[],marker='o',ls='',color=MULTI,ms=4,label='MetaSEQ (C3)')],
              loc='lower center',bbox_to_anchor=(.5,1.03),ncol=2)
    panel(fig,'a',.025,.985,'Same backbone; five response-quality criteria')
    panels=[(.025,.67,.21,.40,'b','Three-judge mean',None),
            (.535,.67,.71,.40,'c','Kimi-K2 judge',['kimi2']),
            (.025,.34,.21,.09,'d','Claude-4-sonnet judge',['claude4']),
            (.535,.34,.71,.09,'e','Qwen3-235B judge',['qwen3'])]
    for labelx,titley,left,bottom,letter,title,judges in panels:
        ax=fig.add_axes([left,bottom,.265,.23])
        for k,(cats,color,marker) in enumerate(zip(td.GROUPS.values(),COLORS,MARKERS)):
            for y,m in enumerate(models):
                mu,hw=td.mean_ci(td.query_scores(data[m],judges,cats))
                ax.errorbar(mu,y+(k-1)*.21,xerr=hw,fmt=marker,ms=3.8,
                            color=color,mfc='white' if k==2 else color,lw=.9,capsize=1.3)
        ax.set(xlim=(.55,1.025),xticks=[.6,.8,1],ylim=(5.6,-.6),yticks=range(6),
               yticklabels=[td.LABELS[m] for m in models],xlabel='Mean judge score')
        clean_axis(ax)
        panel(fig,letter,labelx,titley,title)
    fig.legend(handles=[Line2D([],[],marker=m,ls='',color=c,mfc='white' if k==2 else c,ms=4,label=l)
                        for k,(m,c,l) in enumerate(zip(MARKERS,COLORS,CLASSES))],
               loc='lower center',bbox_to_anchor=(.5,.002),ncol=3,columnspacing=2)
    save(fig,OUT)


if __name__=='__main__':main()
