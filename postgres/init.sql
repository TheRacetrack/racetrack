CREATE SCHEMA IF NOT EXISTS racetrack AUTHORIZATION racetrack;
-- Sample password for local development only
CREATE USER racetrack WITH ENCRYPTED PASSWORD 'dev-25ZjbUDJH6MzmUR';
GRANT ALL PRIVILEGES ON DATABASE racetrack TO racetrack;
ALTER ROLE racetrack SET search_path = racetrack;
