import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { login as apiLogin, me, signup as apiSignup } from "../api/auth";
import type { User } from "../api/types";
import { tokenStorage } from "./tokenStorage";

type AuthState = {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
};

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = tokenStorage.get();
    if (!token) {
      setReady(true);
      return;
    }
    me()
      .then(setUser)
      .catch(() => tokenStorage.clear())
      .finally(() => setReady(true));
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user,
      ready,
      async login(email, password) {
        const res = await apiLogin(email, password);
        tokenStorage.set(res.access_token);
        setUser(res.user);
      },
      async signup(email, password, fullName) {
        await apiSignup(email, password, fullName);
      },
      logout() {
        tokenStorage.clear();
        setUser(null);
      },
    }),
    [user, ready],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth outside provider");
  return ctx;
}
