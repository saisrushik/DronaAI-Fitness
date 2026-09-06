import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../lib/api";

export type Role = "customer" | "coach";

export interface CustomerProfile {
  id: string;
  coach_id: string | null;
  share_code: string;
  date_of_birth: string | null;
  age: number | null;
  gender: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  waist_cm: number | null;
  neck_cm: number | null;
  hip_cm: number | null;
  activity_level: string | null;
  primary_goal: string | null;
  diet_type: string | null;
  dietary_preferences: string[] | null;
  health_injury_history: string[] | null;
  profile_completed: boolean;
}

export interface CoachProfile {
  id: string;
  specialization: string | null;
  years_experience: number | null;
  bio: string | null;
  profile_completed: boolean;
}

export interface HealthMetrics {
  bmi: { value: number; who: string; asian: string };
  bmr: number;
  tdee: number;
  target_calories: number;
  calorie_floor_applied: boolean;
  macros: { protein_g: number; carbs_g: number; fat_g: number };
  body_fat: { value: number; category: string } | null;
  lean_body_mass: number;
  ideal_weight: number;
  healthy_weight: { who: [number, number]; asian: [number, number] };
  heart_rate: { max: number; zones: { name: string; low: number; high: number }[] };
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: Role;
  email_verified: boolean;
  profile_completed: boolean;
  customer: CustomerProfile | null;
  coach: CoachProfile | null;
  metrics: HealthMetrics | null;
}

interface Credentials {
  email: string;
  password: string;
}

export interface RegisterInput {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  role: Role;
  accepted_disclaimer: boolean;
  date_of_birth?: string;
  gender?: string;
  height_cm?: number;
  weight_kg?: number;
  waist_cm?: number;
  neck_cm?: number;
  hip_cm?: number;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (input: Credentials) => Promise<User>;
  register: (input: RegisterInput) => Promise<string>;
  logout: () => Promise<void>;
  setUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // The session cookie is sent automatically, so just ask the API who we are.
  useEffect(() => {
    api
      .get<User>("/auth/me")
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const value: AuthContextValue = {
    user,
    loading,
    login: async (input) => {
      const me = await api.post<User>("/auth/login", input);
      setUser(me);
      return me;
    },
    register: async (input) => {
      const { message } = await api.post<{ message: string }>("/auth/register", input);
      return message;
    },
    logout: async () => {
      await api.post("/auth/logout").catch(() => undefined);
      setUser(null);
    },
    setUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
