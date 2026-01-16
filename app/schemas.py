# schemas.py
from typing import Optional
from pydantic import BaseModel

#########################################################################
##### Uses pydantic for cache/dynamic objects; not referenced in DB #####
#########################################################################

#Docker request schema
class StartDockerRequest(BaseModel):
    image_link: str #dockerhub url
    time_alive: int #seconds
    exercise_name: str #name of the exercise
    competition_name: str #name of the competition
    competition_uuid: str #uuid of the competition
    port: Optional[int] = None #port where the container is interacting

#Docker shutdown schema
class ShutdownDockerRequest(BaseModel):
    container_id: str #container ID

#Docker deletion schema
class DeleteDockerRequest(BaseModel):
    container_id: str #container ID