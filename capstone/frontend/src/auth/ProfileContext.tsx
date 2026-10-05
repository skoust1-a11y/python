import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { createProfile, deleteProfile, listProfiles, type Profile } from "../api/profiles";
import { useAuth } from "./AuthContext";

const KEY = "frii.profileId";

type ProfileState = {
  profiles: Profile[];
  profileId: string;
  setProfileId: (id: string) => void;
  create: (name: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
};

const Ctx = createContext<ProfileState | null>(null);

export function ProfileProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [profiles, setProfiles] = useState<Profile[]>([
    { profile_id: "default", name: "Default (original docs)", kind: "default" },
  ]);
  const [profileId, setProfileIdState] = useState(() => localStorage.getItem(KEY) || "default");

  function setProfileId(id: string) {
    localStorage.setItem(KEY, id);
    setProfileIdState(id);
  }

  useEffect(() => {
    if (!user) return;
    listProfiles()
      .then((r) => {
        setProfiles(r.profiles);
        if (!r.profiles.some((p) => p.profile_id === profileId)) setProfileId("default");
      })
      .catch(() => undefined);
  }, [user, profileId]);

  const value = useMemo<ProfileState>(
    () => ({
      profiles,
      profileId,
      setProfileId,
      async create(name: string) {
        const r = await createProfile(name);
        setProfiles((p) => [...p, r.profile]);
        setProfileId(r.profile.profile_id);
      },
      async remove(id: string) {
        await deleteProfile(id);
        setProfiles((p) => p.filter((row) => row.profile_id !== id));
        if (profileId === id) setProfileId("default");
      },
    }),
    [profiles, profileId],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useProfile() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useProfile");
  return ctx;
}
