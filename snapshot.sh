#!/bin/sh
# Re-export the showcase data from the local platform stack, then rebuild.
# Needs the docker compose stack running. Usage: ./snapshot.sh && git commit -am "refresh showcase"
set -e
cd "$(dirname "$0")"
q(){ docker exec content_my_trip-postgres-1 psql -U cmt_app -At -d "$1" -c "$2"; }
q content_db "select json_agg(row_to_json(d)) from (select id,name,slug,tagline,region,country,main_image,banner_image,best_time_to_visit,ideal_duration,known_for,highlights,description,destination_type,budget_range,nearest_airport,local_food,experiences,attractions from destination where id<>8 order by name) d" > data/destinations.json
q video_db "select json_agg(row_to_json(v)) from (select v.id,v.title,v.description,v.thumbnail_path,v.youtube_url,v.instagram_url,v.facebook_url,v.tiktok_url,v.published_at,v.uploader_id,v.is_portrait,v.hashtags,(select array_agg(destination_id) from video_destination vd where vd.video_id=v.id) as destination_ids from video v where v.status='published' order by v.published_at desc nulls last) v" > data/videos.json
q auth_db "select json_agg(row_to_json(u)) from (select id,username,name,bio,profile_photo,home_destination_id,is_featured,created_at from \"user\" where role='creator' and is_active order by id) u" > data/creators.json
q auth_db "select json_agg(row_to_json(u)) from (select id,name,username from \"user\" where id in (select distinct uploader_id from dblink('dbname=video_db user=cmt_app','select uploader_id from video where status=''published''') as t(uploader_id int))) u" > data/uploaders.json 2>/dev/null || echo "uploaders.json: refresh manually (dblink not installed)"
q creator_db "select json_agg(row_to_json(e)) from (select creator_id, count(*) as edits from edit_assignment where status in ('completed','approved','delivered') group by creator_id) e" > data/edits.json
echo "data refreshed; copy any new images from the containers' /app/static/uploads into assets/img (see build.py img()) then: python3 build.py"
