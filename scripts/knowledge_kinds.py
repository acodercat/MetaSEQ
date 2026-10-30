"""A post hoc grouping of the 111 experiment-2 tasks by the kind of environmental knowledge each
turns on, used only in the Supplementary Information (Supplementary Table 30 and the kind column
of Supplementary Note 4). Each task was assigned from its text to one kind. The grouping was
made after the per-category pass rates of A and D had been seen and before any per-kind result
was computed; it is exploratory."""

KINDS = {
    "regulatory": """beijing_annual_pm25_station_screen beijing_aqi_aggregation_order beijing_aqi_co_unit
        beijing_aqi_primary_pollutant beijing_attainment_days beijing_o3_percentile_metric
        beijing_ozone_ppb_standard beijing_two_standards_unnamed hk_aqo_revision_allowance
        hk_aqo_station_level_compliance hk_ozone_aqo_day_boundary hk_ozone_burden_year_on_year
        hk_ozone_peak_season_aqo hk_photochemical_episode_aqhi_encoding
        hk_pm25_annual_aqo_provisional_record beijing_compound_pollution_days
        beijing_o3_mda8_exceedance beijing_exceedance_exposure_bias hk_aqhi_not_reproducible
        hk_aqhi_briefing_summary hk_roadside_index_compression beijing_channel_city_membership
        beijing_w126_vegetation_exposure""",
    "attribution": """beijing_lockdown_paradox beijing_regional_trend_attribution hk_cny_traffic_quasi_experiment
        beijing_fire_detection_bias hk_kwai_chung_so2_port_signature beijing_spring_sector_tail
        beijing_wind_sector_pm25 hk_airmass_origin_ozone beijing_box_model_flux
        beijing_olympics_meteorological_adjustment hk_traffic_no2_diurnal_confounding
        beijing_rush_hour_paradox hk_cyclone_approach_and_passage beijing_sharpest_cleanout
        beijing_dust_recovery hk_tap_mun_sea_salt_coarse hk_ozone_and_pm_episode_meteorology""",
    "physics": """beijing_aerosol_beer_lambert_mean beijing_inversion_potential_temp
        beijing_wind_recirculation_transport beijing_ventilation_dilution_law hk_bulk_richardson_screen
        hk_inversion_convective_instability hk_inversion_species_response hk_layer_moisture_transport
        hk_moist_hypsometric_thickness hk_potential_instability_despite_dry_stability
        hk_radiation_photolysis_proxy hk_freezing_level_phase_limit hk_partial_column_water_mass
        hk_moisture_mixing_ratio_rank hk_daily_clearness_seasonality hk_visibility_extinction_aggregation
        hk_vpd_evaporative_demand beijing_below_ground_level hk_cloud_enhancement_extreme
        hk_nocturnal_decoupling_morning_fumigation""",
    "chemistry": """beijing_no3_production_kinetics beijing_n2o5_equilibrium_partition
        hk_water_vapour_oh_no2_rate_enhancement beijing_nocturnal_titration hk_roadside_oxidant_titration
        hk_roadside_night_cleanliness hk_weekend_ozone_ox_conservation beijing_weekend_ozone_regime_reversal
        beijing_o3_climate_penalty hk_sunshine_ozone_scale_reversal beijing_haze_vs_dust_episode
        beijing_fine_fraction_2020 hk_april_2025_coarse_dust_signature beijing_dust_column_vs_surface""",
    "statistics": """beijing_forecast_skill_floor hk_ozone_probability_skill hk_pm25_forecast_leakage
        beijing_regression_to_mean beijing_multiple_comparisons beijing_trend_uncertainty
        beijing_wind_circular_mean beijing_interpolation_skill beijing_realtime_anomaly_lookahead
        beijing_aerosol_compositional_closure hk_lur_coefficient_identifiability""",
    "provenance": """beijing_station_coordinate_audit beijing_complete_case_bias beijing_product_provenance
        hk_pressure_datum_mismatch hk_solar_sampling_aliasing hk_stuck_analyser_constant_run
        hk_weather_variable_coverage hk_radiation_sensor_failure hk_calm_coded_as_north
        beijing_so2_reporting_floor hk_co_availability_selection_bias hk_hot_nights_hourly_ceiling
        hk_very_hot_days_hourly_floor hk_pm25_change_coverage_pushback hk_wind_change_record_start_pushback
        hk_no2_trend_network_change hk_ventilation_evidence_span beijing_cams_dust_regime_validation
        hk_era5_grid_choice_instability beijing_era5_grid_pseudoreplication beijing_partial_year_baseline
        hk_extreme_wind_corroboration""",
    "geospatial": """beijing_monitor_catchment_imbalance hk_population_weighted_background_no2
        hk_receptor_station_representativeness beijing_dust_front_speed""",
}
KIND_LABELS = {"regulatory": "Regulatory conventions", "attribution": "Causal attribution",
               "physics": "Atmospheric physics", "chemistry": "Atmospheric chemistry",
               "statistics": "Statistical inference", "provenance": "Data provenance",
               "geospatial": "Geospatial exposure"}
KIND_ORDER = list(KIND_LABELS)
KIND_OF = {t: k for k, s in KINDS.items() for t in s.split()}
assert len(KIND_OF) == 111 == sum(len(s.split()) for s in KINDS.values()), "every task in exactly one kind"
