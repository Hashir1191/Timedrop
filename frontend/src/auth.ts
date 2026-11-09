import { createContext, useContext } from "react";
import type { User } from "./types";

export type AuthState = { token: string | null; user: User | null; loading: boolean };
export type AuthContextValue = AuthState & {
  setAuth: (value: AuthState) => void;
  logout: () => void;
};
export const AuthContext = createContext<AuthContextValue | null>(null);
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthContext.Provider");
  return value;
}