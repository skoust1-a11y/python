## Project Context

In earlier practice, you made your Trip & Travel Planner Agent interactive using **React**.  
However, it was still open to everyone — anyone with the URL could use it.  

In this practice, you will secure your agent using **Auth0**.  
You’ll configure user roles (admin, user), and protect your **FastAPI** backend so only authenticated and authorized users can access it.  
 

---

## Problem Statement

Implement secure authentication and authorization for your Travel Agent using **Auth0**, **React**, and **FastAPI**.  
You’ll complete three main tasks corresponding to the three learning objectives.

---

### **Task 1 — Configure Auth0 with Roles**

#### Goal  
Create and configure a secure identity layer in Auth0.

#### Requirements  
1. Create an API in Auth0.    
2. Create an application in Auth0.   
3. Create **admin** and **user** role.
4. Create users and assign roles manually. 
5. Add one **Auth0 Actions**:  
   - `add-roles-to-tokens` → adds roles to JWT.  
6. Test login for different users and  roles.  
  

---

### **Task 2 — Integrate Auth0 SDK in React**

#### Goal  
Connect your React frontend to Auth0 for login/logout and role-based UI.

#### Requirements  
1. Install the SDK:  
   ```bash
   npm install @auth0/auth0-react ```

2. Update `.env` with required environment variable.  

3. In `main.tsx` wrap your <App> component with the Auth0 provider.

4. In `App.tsx`:  
   - Use `useAuth0()` hook to get the roles of the login user.  
   - Implement Log In and Log Out button.
   -  Based on role conditionally display the chat component for user and admin welcome message for admin.
    

**Expected Output:**  
- Non-authenticated users see “Please log in to access the chat.”  
- Authenticated users can chat.  
- Authenticated admins see the “Welcome Admin” message.

---

### **Task 3 — Protect FastAPI Backend with JWT Validation**

#### Goal  
Add a security middleware that validates Auth0 JWT tokens and permits only authorized users.

#### Requirements  
1. Install the required dependencies.  
   
2. Complete the security.py file to handle JWT authentication and authorization.
  
3. Protect the chat endpoint with JWT authentication.

### **Task 4 - In the frontend include the token in API call**


**Expected Output:**  
- Authenticated users →  200 OK (chat response).  
- Admin → Welcome message
- Unauthorized user →  403 / 401 error.  

## Evaluation Criteria

Ensure you evaluate your solution against the bellow criteria:

1. **Auth Protection**: Ensure the frontend is wrapped with `<Auth0Provider>` from `@auth0/auth0-react` library properly so that only authenticated users can access protected areas.
2. **Role Display**: Make sure the frontend correctly shows the chat component or the admin welcome message based on the user’s assigned roles.
3. **Token Forwarding**: Ensure the frontend includes the JWT token in every backend request for secure authentication by getting access token.
4. **Token Validation**: Complete the security.py file to handle JWT authentication and authorization.
