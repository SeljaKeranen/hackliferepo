# Dataset register

Access decision: 11 September 2026. Only public aggregate country data is used. API responses stay in ignored `data/`; the demo contains derived country summaries and fitted parameters.

| Dataset | Definition and use | Licence and source |
|---|---|---|
| WDI, SP.DYN.LE00.IN | Life expectancy at birth, total, years. Outcome; UN Population Division and national statistical sources. Period life expectancy, not an individual lifespan prediction. | [World Bank indicator](https://data.worldbank.org/indicator/SP.DYN.LE00.IN), CC BY 4.0 |
| WDI, SH.XPD.CHEX.GD.ZS | Current health expenditure, percentage of GDP; WHO Global Health Expenditure Database. Predictor, not government spending alone. | [Indicator](https://data.worldbank.org/indicator/SH.XPD.CHEX.GD.ZS), CC BY 4.0 |
| WDI, NY.GDP.PCAP.PP.KD | GDP per capita, PPP, constant 2021 international dollars. Log transformed predictor. | [Indicator](https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.KD), CC BY 4.0 |
| WDI, EN.ATM.PM25.MC.M3 | Population-weighted mean annual PM2.5 exposure, micrograms per cubic metre. GBD-derived series distributed through WDI. | [Indicator](https://data.worldbank.org/indicator/EN.ATM.PM25.MC.M3), World Bank distribution labelled CC BY 4.0; no restricted upstream download |
| WDI, SH.PRV.SMOK | Current tobacco use, ages 15+, modelled. Context only because observations are sparse. Includes smoked and smokeless tobacco; excludes e-cigarettes. | [Indicator](https://data.worldbank.org/indicator/SH.PRV.SMOK), CC BY 4.0; [WHO definition](https://www.who.int/data/gho/indicator-metadata-registry/imr-details/prevalence-of-current-tobacco-use-among-persons-aged-15-years-and-older-age-standardized) |
| WDI, SP.POP age/sex indicators | Population composition by five-year age group; observed demographic context. Each denominator comes from the indicator title and is transformed explicitly. | [WDI population indicators](https://data.worldbank.org/topic/population), CC BY 4.0; exact series recorded by downloader |
| Natural Earth / world-atlas 2.0.2 | Simplified country boundaries, display only. | [Natural Earth terms](https://www.naturalearthdata.com/about/terms-of-use/), public domain; [world-atlas](https://github.com/topojson/world-atlas), ISC packaging |
| Official policy documents | Factual paraphrases, dated links, short excerpts and content fingerprints for review. Not model training data. | Public access does not imply an open licence. Full documents are not redistributed. Publisher and URL retained per record. |

World Bank [terms](https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets) and [licence explanation](https://datacatalog.worldbank.org/public-licenses) apply. Release attribution: World Bank, World Development Indicators, underlying providers as recorded, retrieved 11 September 2026; transformed by Longview. Exact retrieval timestamps, API revision dates, URLs and hashes are stored locally. Missing values remain missing. Historical data is the current revised vintage; evaluation cannot reconstruct what was published at each historical forecast date.

You.com and Tavily discover sources; they are not factual authorities or dataset licences. The combined search/extraction cap is 500 attempted requests including retries and seven planning requests already made. No credit purchase is authorised. Provider responses and raw source caches remain local.

The app bundles Inter (SIL Open Font License 1.1) from `@fontsource/inter`; see the packaged font licence. [National-series reconciliation](data-reconciliation.md) records differences from national headline estimates.
