Build: 
docker-compose up --build -d

API logs: 
docker-compose logs fastapi_app

Run tests: 
docker-compose exec fastapi_app pytest

Swagger: 
http://localhost:8000/docs#/

Future improvements: 
Hash API-Keys with bcrypt
Add documentation and comments
More unittests