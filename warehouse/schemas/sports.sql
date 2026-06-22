-- Sports Analytics Data Warehouse - Star Schema
-- European Soccer Database
-- Drop and recreate tables with proper distribution and sort keys

-- Drop tables if exist
DROP TABLE IF EXISTS fact_matches CASCADE;
DROP TABLE IF EXISTS dim_teams CASCADE;
DROP TABLE IF EXISTS dim_players CASCADE;
DROP TABLE IF EXISTS dim_leagues CASCADE;
DROP TABLE IF EXISTS dim_dates CASCADE;

-- Dimension: Teams
CREATE TABLE dim_teams (
    team_id VARCHAR(64) NOT NULL ENCODE lzo,
    team_api_id BIGINT ENCODE az64,
    team_name VARCHAR(200) ENCODE lzo,
    team_short_name VARCHAR(10) ENCODE lzo,
    team_long_name VARCHAR(200) ENCODE lzo,
    country VARCHAR(50) ENCODE lzo,
    founded_year INTEGER ENCODE az64,
    stadium_name VARCHAR(200) ENCODE lzo,
    stadium_capacity INTEGER ENCODE az64,
    is_active BOOLEAN ENCODE runlength,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (team_id)
)
DISTSTYLE ALL
SORTKEY (team_id);

-- Dimension: Players
CREATE TABLE dim_players (
    player_id VARCHAR(64) NOT NULL ENCODE lzo,
    player_api_id BIGINT ENCODE az64,
    player_name VARCHAR(200) ENCODE lzo,
    birthday DATE ENCODE az64,
    age INTEGER ENCODE az64,
    height DECIMAL(5,2) ENCODE az64,
    weight DECIMAL(5,2) ENCODE az64,
    nationality VARCHAR(50) ENCODE lzo,
    preferred_foot VARCHAR(10) ENCODE lzo,
    position VARCHAR(50) ENCODE lzo,
    overall_rating INTEGER ENCODE az64,
    potential INTEGER ENCODE az64,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (player_id)
)
DISTSTYLE ALL
SORTKEY (player_id);

-- Dimension: Leagues
CREATE TABLE dim_leagues (
    league_id VARCHAR(64) NOT NULL ENCODE lzo,
    league_name VARCHAR(200) ENCODE lzo,
    country VARCHAR(50) ENCODE lzo,
    league_level INTEGER ENCODE az64,
    division VARCHAR(50) ENCODE lzo,
    confederation VARCHAR(10) ENCODE lzo,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (league_id)
)
DISTSTYLE ALL
SORTKEY (league_id);

-- Dimension: Dates
CREATE TABLE dim_dates (
    date_id DATE NOT NULL ENCODE az64,
    year INTEGER ENCODE az64,
    quarter INTEGER ENCODE az64,
    month INTEGER ENCODE az64,
    month_name VARCHAR(10) ENCODE lzo,
    week INTEGER ENCODE az64,
    day INTEGER ENCODE az64,
    day_of_week INTEGER ENCODE az64,
    day_name VARCHAR(10) ENCODE lzo,
    is_weekend BOOLEAN ENCODE runlength,
    is_holiday BOOLEAN ENCODE runlength,
    PRIMARY KEY (date_id)
)
DISTSTYLE ALL
SORTKEY (date_id);

-- Fact: Matches
CREATE TABLE fact_matches (
    match_id VARCHAR(64) NOT NULL ENCODE lzo,
    match_api_id BIGINT ENCODE az64,
    league_id VARCHAR(64) NOT NULL ENCODE lzo,
    season_year INTEGER ENCODE az64,
    match_date DATE ENCODE az64,
    home_team_id VARCHAR(64) NOT NULL ENCODE lzo,
    away_team_id VARCHAR(64) NOT NULL ENCODE lzo,
    home_team_goal INTEGER ENCODE az64,
    away_team_goal INTEGER ENCODE az64,
    total_goals INTEGER ENCODE az64,
    goal_difference INTEGER ENCODE az64,
    match_result VARCHAR(10) ENCODE lzo,  -- Home Win, Away Win, Draw
    is_home_win BOOLEAN ENCODE runlength,
    is_away_win BOOLEAN ENCODE runlength,
    is_draw BOOLEAN ENCODE runlength,
    home_possession INTEGER ENCODE az64,
    away_possession INTEGER ENCODE az64,
    home_shots INTEGER ENCODE az64,
    away_shots INTEGER ENCODE az64,
    home_shots_on_target INTEGER ENCODE az64,
    away_shots_on_target INTEGER ENCODE az64,
    home_corners INTEGER ENCODE az64,
    away_corners INTEGER ENCODE az64,
    home_fouls INTEGER ENCODE az64,
    away_fouls INTEGER ENCODE az64,
    home_yellow_cards INTEGER ENCODE az64,
    away_yellow_cards INTEGER ENCODE az64,
    home_red_cards INTEGER ENCODE az64,
    away_red_cards INTEGER ENCODE az64,
    attendance INTEGER ENCODE az64,
    stadium VARCHAR(200) ENCODE lzo,
    referee VARCHAR(200) ENCODE lzo,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (match_id),
    FOREIGN KEY (league_id) REFERENCES dim_leagues(league_id),
    FOREIGN KEY (home_team_id) REFERENCES dim_teams(team_id),
    FOREIGN KEY (away_team_id) REFERENCES dim_teams(team_id)
)
DISTSTYLE KEY
DISTKEY (league_id)
SORTKEY (match_date, season_year, league_id);

-- Create aggregate table for team statistics
CREATE TABLE fact_team_stats_season (
    team_id VARCHAR(64) NOT NULL ENCODE lzo,
    league_id VARCHAR(64) NOT NULL ENCODE lzo,
    season_year INTEGER NOT NULL ENCODE az64,
    matches_played INTEGER ENCODE az64,
    wins INTEGER ENCODE az64,
    draws INTEGER ENCODE az64,
    losses INTEGER ENCODE az64,
    goals_scored INTEGER ENCODE az64,
    goals_conceded INTEGER ENCODE az64,
    goal_difference INTEGER ENCODE az64,
    points INTEGER ENCODE az64,
    home_wins INTEGER ENCODE az64,
    away_wins INTEGER ENCODE az64,
    clean_sheets INTEGER ENCODE az64,
    yellow_cards INTEGER ENCODE az64,
    red_cards INTEGER ENCODE az64,
    avg_possession DECIMAL(5,2) ENCODE az64,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    PRIMARY KEY (team_id, league_id, season_year)
)
DISTSTYLE KEY
DISTKEY (team_id)
SORTKEY (season_year, league_id);

-- Grant permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO GROUP analytics_users;
GRANT ALL ON ALL TABLES IN SCHEMA public TO GROUP etl_users;

-- Analyze tables
ANALYZE dim_teams;
ANALYZE dim_players;
ANALYZE dim_leagues;
ANALYZE dim_dates;
ANALYZE fact_matches;
ANALYZE fact_team_stats_season;

-- Comments
COMMENT ON TABLE dim_teams IS 'Team dimension with club information';
COMMENT ON TABLE dim_players IS 'Player dimension with attributes and ratings';
COMMENT ON TABLE dim_leagues IS 'League dimension with competition details';
COMMENT ON TABLE fact_matches IS 'Match fact table with detailed statistics';
COMMENT ON TABLE fact_team_stats_season IS 'Aggregated team statistics by season';
