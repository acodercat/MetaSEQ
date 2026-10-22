"""Query-paired preference rates, recomputed from local archived rankings."""
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from data_figure_style import setup,save,clean_axis,WIDTH,MM,INK,MUTED,MULTI,GRID
setup()
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'phase1_evaluation/eval_results/compare/hk'
OUT=ROOT/'manuscript/figures/win_loss.pdf'
CATS=['Temporal pattern analysis','Geospatial analysis','Multivariate analysis',
      'Urban environmental planning','Environmental decision support','Personal action planning']


def wilson(w,n,z=1.959964):
    p=w/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return c-h,c+h


def main():
    rows=[]
    for i,name in enumerate(CATS,1):
        data=json.loads((BASE/f'hk_cat_{i}_judge_claude4_compare_results.json').read_text())
        rows.append((name,sum(x.get('ranking',{}).get('claude4')==1 for x in data),len(data)))
    w,n=sum(r[1] for r in rows),sum(r[2] for r in rows);assert(w,n)==(89,117)
    rows.append(('Pooled',w,n))
    fig=plt.figure(figsize=(WIDTH,84*MM));ax=fig.add_axes([.34,.17,.44,.73])
    for i,(name,w,n) in enumerate(rows):
        y=i+(0.4 if name=='Pooled' else 0);lo,hi=np.array(wilson(w,n))*100;p=100*w/n
        ax.errorbar(p,y,xerr=[[p-lo],[hi-p]],fmt='D' if name=='Pooled' else 'o',
                    color=MULTI,ms=5 if name=='Pooled' else 4.5,lw=.9,capsize=2)
        ax.text(104,y,f'{p:.1f}%  ({w}/{n})',ha='left',va='center',fontsize=7,
                weight='bold' if name=='Pooled' else 'normal',clip_on=False)
    ax.axvline(50,color=MUTED,lw=.7,ls=(0,(3,2)))
    ax.set(xlim=(30,100),xticks=[30,50,75,100],ylim=(7,-.6),yticks=[0,1,2,3,4,5,6.4],
           yticklabels=[r[0] for r in rows],xlabel='Preference for MetaSEQ (%)')
    ax.get_yticklabels()[-1].set_weight('bold');clean_axis(ax)
    fig.text(.34,.96,'Point estimate and 95% Wilson interval',fontsize=7,weight='bold')
    fig.text(.80,.96,'Queries preferred',fontsize=7,weight='bold')
    save(fig,OUT)


if __name__=='__main__':main()
