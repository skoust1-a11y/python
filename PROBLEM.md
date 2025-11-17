
# Sprint 8 Practice Assignment: Securing the Trip & Travel Planner Agent

## Project Context

In **Sprint 7**, you made your Trip & Travel Planner Agent interactive using **Streamlit** and **React**.  
However, it was still open to everyone — anyone with the URL could use it.  

In **Sprint 8**, you will secure your agent using **Auth0**, a professional identity provider.  
You’ll configure user roles (admin), enable social logins (like Google), and protect your **FastAPI** backend so only authenticated and authorized users can access it.  
By the end, your app will be fully **authenticated** and  **authorized**.

---

## Problem Statement

Your task is to **implement secure authentication and authorization** for your Travel Agent using **Auth0**, **React**, and **FastAPI**.  
You’ll complete three main tasks corresponding to the three learning objectives.

---

### **Task 1 — Configure Auth0 with Roles and Social Login**

## Notes : Follow the complete steps given in **Manual User Management in Auth0** PDF and **Enable Social Media Login in Auth0** PDF.


#### Goal  
Create and configure a secure identity layer in Auth0.

#### Requirements  
1. Create an **API** in Auth0:  
   - Name : `Trip and Travel Agent API`  
   - Identifier : `https://api.trip-travel-agent.com`  
   - Enable RBAC and “Add permissions in Access Token”.  

2. Create an **Application**:  
   - Name : `Trip and Travel agent Frontend`  
   - Type : `Single Page Application`  
   - Add callback/logout URLs → `http://localhost:5173`.  

3. Create **roles**:  
   - `admin` — Administrator of Trip and Travel Agent  

4. Create users and assign roles manually.  

5. Enable **Google Social Login**:  
   - Configure OAuth Client in Google Cloud Console.  
   - Add Google Connection in Auth0. 

6. Google Social Login only for the users without any role. 

  
7. Test login for:  
   - Manual users with the admin role should see the admin view; all other manual users should see the chat interface.
   - Social login users should have access to the chat view.
 

**Expected Output:**  
Every user (email/password or social) receives a JWT token containing a `roles` claim.

---

### **Task 2 — Integrate Auth0 SDK in React**

#### Goal  
Connect your React frontend to Auth0 for login/logout and role-based UI.

#### Requirements  
1. Install the SDK:  
   ```bash
   npm install
   ```

2. Add `.env`:  
   ```bash
   VITE_AUTH0_DOMAIN=your-domain
   VITE_AUTH0_CLIENT_ID=your-client-id
   VITE_AUTH0_AUDIENCE=https://api.trip-travel-agent.com
   VITE_AUTH0_ROLE_NAMESPACE=https://trip-travel-agent.com/
   ```

3. Wrap `<App />` inside `<Auth0Provider />` in `main.tsx`.  

4. In `App.tsx`:  
   - Use `useAuth0()` hook.  
   - Show “Log In / Log Out” buttons.  
   - For no role, render `<ChatComponent />`.  
   - If role = **admin**, show admin welcome message.  

**Expected Output:**  
- Non-authenticated users see “Please log in to access the chat.”  
- Authenticated users without role can chat.  
- Authenticated with Admins role can see “Welcome Admin” message.

---

### **Task 3 — Protect FastAPI Backend with JWT Validation**

#### Goal  
Add a security middleware that validates Auth0 JWT tokens and permits only authorized users.

#### Requirements  
1. Install dependencies:  
   ```bash
   uv sync
   ```

2. Create `security.py` to:  
   - Fetch JWKS (public keys) from Auth0.  
   - Validate JWT signature and claims (`iss`, `aud`, `exp`).  
   - Return decoded payload on success or 401 on failure.

3. In `main.py`:  
   - Import `validate_token` dependency.  
   - Add CORS middleware for `http://localhost:5173`.  
   - Protect the `/chat` endpoint:  
     - Reject requests without valid JWT.  
   

4. From React frontend, include token in API calls:  
   ```js
   const token = await getAccessTokenSilently();
   const response = await fetch("/chat", {
     headers: { Authorization: `Bearer ${token}` },
   });
   ```

**Expected Output:**  
- Authenticated users with role `user` →  200 OK (chat response).  
- Admin or unauthorized user →  403 / 401 error.  

---

##  Expected Outcome

| Concept | Demonstrated Through |
|----------|----------------------|
| Auth0 setup with roles + social login | Task 1 |
| React integration using Auth0 SDK | Task 2 |
| Backend protection via JWT middleware | Task 3 |

---

##  By the End of This Sprint

You’ll have a **secure, full-stack Travel Agent** application where:  
- Only authenticated users can chat.  
- Roles determine access level.  
- Frontend and backend communicate securely via JWT tokens.