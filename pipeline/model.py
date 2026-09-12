"""Five-year country forecasts with temporal and country holdouts.

Specification is fixed before viewing test scores: tune on origin 2009;
rolling tests at origins 2014..2019; hold SE/US/SG out of all fitting and tuning.
Covariates are lagged one observation year. Current revised vintage remains a limitation.
"""
import json
import math
import hashlib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from .store import ROOT, DATA, COUNTRIES, connect, write_json, now, digest
from .data import INDICATORS, AGE_GROUPS

FEATURES=['life_expectancy','past_change','log_gdp','health_spending','pm25']
HOLDOUT={'SWE','USA','SGP'}

def panel():
    with connect() as db: df=pd.read_sql_query('SELECT * FROM observations',db)
    eligible=json.loads((DATA/'countries.json').read_text())
    df=df[df.country.isin(eligible)]
    p=df.pivot(index=['country','year'],columns='dataset_id',values='value').reset_index()
    p=p.rename(columns={k:v[0] for k,v in INDICATORS.items()})
    rows=[]
    for country,g in p.groupby('country'):
        g=g.set_index('year').sort_index()
        for year,r in g.iterrows():
            if year<2001 or year>2024 or year-5 not in g.index or year-1 not in g.index: continue
            lag=g.loc[year-1]
            if pd.isna(r.get('life_expectancy')) or pd.isna(g.loc[year-5].get('life_expectancy')): continue
            row={'country':country,'year':int(year),'feature_year':int(year)-1,'life_expectancy':r.life_expectancy,'past_change':r.life_expectancy-g.loc[year-5].life_expectancy,'log_gdp':np.log(lag.get('gdp_ppp')) if lag.get('gdp_ppp',0)>0 else np.nan,'health_spending':lag.get('health_spending',np.nan),'pm25':lag.get('pm25',np.nan),'target':g.loc[year+5].life_expectancy-r.life_expectancy if year+5 in g.index else np.nan}
            rows.append(row)
    all_rows=pd.DataFrame(rows)
    complete=all_rows.dropna(subset=FEATURES).copy()
    return p,complete,{'candidate_rows':len(all_rows),'complete_rows':len(complete),'excluded_missing_inputs':len(all_rows)-len(complete),'rule':'Complete cases only; no interpolation, forward fill or zero imputation.'}

def fit(train,alpha):
    scaler=StandardScaler().fit(train[FEATURES])
    reg=Ridge(alpha=alpha).fit(scaler.transform(train[FEATURES]),train.target)
    return scaler,reg

def predict(model,frame): return model[1].predict(model[0].transform(frame[FEATURES]))

def params(model,train):
    scaler,reg=model
    return {'features':FEATURES,'mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),'coefficients':reg.coef_.tolist(),'intercept':float(reg.intercept_),'bounds':{f:[float(train[f].min()),float(train[f].max())] for f in FEATURES}}

def infer(p,x):
    return float(p['intercept']+sum(c*(v-m)/s for c,v,m,s in zip(p['coefficients'],x,p['mean'],p['scale'])))

def metrics(rows):
    if not rows:return {'n':0,'mae':None,'coverage':None}
    return {'n':len(rows),'mae':float(np.mean([abs(r['actual']-r['predicted']) for r in rows])),'coverage':float(np.mean([abs(r['actual']-r['predicted'])<=r['radius'] for r in rows]))}

def main():
    observed,all_rows,missing=panel()
    labelled=all_rows.dropna(subset=['target']).copy()
    external=labelled[~labelled.country.isin(HOLDOUT)]
    tune_train=external[external.year+5<=2009]
    validation=external[external.year==2009]
    # Deterministic country split separates alpha/model selection from interval calibration.
    tuning=validation[validation.country.map(lambda c:int(hashlib.sha256(c.encode()).hexdigest(),16)%2==0)]
    calibration=validation[~validation.country.isin(tuning.country)]
    candidates=[]
    for alpha in [0.1,1.,10.,100.,1000.]:
        m=fit(tune_train,alpha)
        candidates.append((float(np.mean(abs(predict(m,tuning)-tuning.target))),alpha))
    ridge_val,alpha=min(candidates)
    scores={'ridge':ridge_val,'no_change':float(np.mean(abs(tuning.target))),'trend':float(np.mean(abs(tuning.past_change-tuning.target)))}
    # Select without looking at the rolling test set.
    selected=min(scores,key=scores.get)
    calibrated=fit(tune_train,alpha)
    val_pred={'ridge':predict(calibrated,calibration),'no_change':np.zeros(len(calibration)),'trend':calibration.past_change.to_numpy()}
    radii={k:float(np.quantile(abs(v-calibration.target.to_numpy()),min(1,math.ceil((len(calibration)+1)*.9)/len(calibration)),method='higher')) for k,v in val_pred.items()}
    evaluations=[];splits=[]
    for origin in range(2014,2020):
        train=external[external.year+5<=origin]
        test=labelled[labelled.year==origin]
        assert train.year.max()+5<=origin and not set(train.country)&HOLDOUT
        m=fit(train,alpha)
        predictions={'ridge':predict(m,test),'no_change':np.zeros(len(test)),'trend':test.past_change.to_numpy()}
        splits.append({'origin':origin,'latest_training_origin':int(train.year.max()),'latest_training_outcome':int(train.year.max())+5,'training_rows':len(train),'test_rows':len(test)})
        for kind,values in predictions.items():
            for (_,row),value in zip(test.iterrows(),values):
                evaluations.append({'country':row.country,'origin':origin,'outcome_year':origin+5,'model':kind,'actual':float(row.target),'predicted':float(value),'radius':radii[kind],'country_held_out':row.country in HOLDOUT})
    final_train=external[external.year+5<=2024]
    final_model=fit(final_train,alpha);exported=params(final_model,final_train)
    report={'generated_at':now(),'specification':'Preselected 2009 tuning origin, disjoint calibration countries; test origins 2014–2019. One-year lag for GDP, health expenditure and PM2.5. Sweden, US and Singapore excluded from all fitting, tuning and calibration.','selected_model':selected,'alpha':alpha,'validation_mae':scores,'validation_n':len(tuning),'calibration_n':len(calibration),'interval_nominal':.9,'interval_radius':radii,'test':{k:metrics([r for r in evaluations if r['model']==k and not r['country_held_out']]) for k in scores},'country_holdout':{c:{k:metrics([r for r in evaluations if r['country']==c and r['model']==k]) for k in scores} for c in sorted(HOLDOUT)},'test_splits':splits,'training_rows':len(final_train),'training_countries':int(final_train.country.nunique()),'missingness':missing,'worst_errors':sorted([r for r in evaluations if r['model']==selected],key=lambda r:abs(r['actual']-r['predicted']),reverse=True)[:8],'limitations':['Current revised data vintage, not historical publication vintages. A one-year observation lag does not prove historical availability.','Overlapping five-year tests and repeated countries are dependent; nominal interval coverage has no exchangeability guarantee.','COVID-era outcomes are included. Structural breaks, omitted variables and country-specific institutions limit transfer.','GDP, spending and pollution coefficients are associations. User changes do not estimate a policy effect.','Ten-year scenarios iterate twice with fixed covariates; no ten-year validation or calibrated ten-year interval.']}
    countries=[];parity=[]
    for iso2,(slug,iso3,name) in COUNTRIES.items():
        country_rows=all_rows[all_rows.country==iso3]
        latest=country_rows.sort_values('year').iloc[-1]
        year=int(latest.year);x=[float(latest[f]) for f in FEATURES]
        delta={'ridge':infer(exported,x),'trend':float(latest.past_change),'no_change':0.}[selected]
        history=observed[(observed.country==iso3)&(observed.year>=1995)].dropna(subset=['life_expectancy'])
        pyramid_rows=observed[(observed.country==iso3)&(observed.year==2024)]
        pyramid=[]
        if len(pyramid_rows):
            row=pyramid_rows.iloc[0]
            for age in AGE_GROUPS:
                male=row.get(f'SP.POP.{age}.MA.5Y');female=row.get(f'SP.POP.{age}.FE.5Y')
                if pd.notna(male) and pd.notna(female):pyramid.append({'age':'80+' if age=='80UP' else f'{int(age[:2])}–{int(age[2:])}','male':float(male),'female':float(female)})
        tobacco=observed[(observed.country==iso3)].dropna(subset=['tobacco']).sort_values('year')
        countries.append({'id':iso2,'iso3':iso3,'slug':slug,'name':name,'origin':year,'input_year':year-1,'features':dict(zip(FEATURES,x)),'latest':x[0],'forecast':x[0]+delta,'forecast_year':year+5,'radius':radii[selected],'history':[{'year':int(r.year),'value':float(r.life_expectancy)} for _,r in history.iterrows()],'pyramid':pyramid,'pyramid_year':2024,'pyramid_unit':'% within each sex; the male and female sides each sum to 100%','tobacco':{'year':int(tobacco.iloc[-1].year),'value':float(tobacco.iloc[-1].tobacco)} if len(tobacco) else None,'holdout_metrics':report['country_holdout'][iso3][selected]})
        parity.append({'country':iso2,'features':x,'expected_delta':infer(exported,x)})
    with connect() as db:datasets=[dict(r) for r in db.execute('SELECT * FROM datasets')]
    public={'release_id':digest({'parameters':exported,'countries':countries,'report':report})[:12],'created_at':now(),'model':dict(exported,selected=selected,interval_radius=radii,alpha=alpha),'countries':countries,'evaluation':report,'datasets':datasets,'attribution':'World Bank, World Development Indicators, underlying providers as recorded. CC BY 4.0. Retrieved 11 September 2026; transformed by Longview.'}
    write_json(ROOT/'public/release/quantitative.json',public)
    write_json(ROOT/'docs/model-evaluation.json',report)
    write_json(DATA/'evaluation-rows.json',evaluations)
    write_json(ROOT/'tests/inference-cases.json',parity)
    print(json.dumps({'selected':selected,'validation':scores,'test':report['test'],'holdout':report['country_holdout'],'training_countries':report['training_countries'],'training_rows':report['training_rows'],'countries':[{'name':c['name'],'origin':c['origin'],'life_expectancy':c['latest'],'forecast':c['forecast']} for c in countries]},indent=2))

if __name__=='__main__':main()
