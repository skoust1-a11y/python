# security.py
import os
import time
import requests
from typing import Dict, Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from dotenv import load_dotenv

load_dotenv()

## Task 3 - Complete the security.py file to handle JWT authentication and authorization.

