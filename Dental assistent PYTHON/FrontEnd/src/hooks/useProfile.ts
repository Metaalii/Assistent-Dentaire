import { useState, useEffect } from "react";

export interface DentistProfile {
  name: string;
  title: string;
  address: string;
  phone: string;
  email: string;
}

const PROFILE_KEY = "dental-assistant-profile";

const DEFAULT_PROFILE: DentistProfile = {
  name: "",
  title: "",
  address: "",
  phone: "",
  email: "",
};

export function useProfile() {
  const [profile, setProfileState] = useState<DentistProfile | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(PROFILE_KEY);
    if (stored) {
      try {
        setProfileState(JSON.parse(stored));
      } catch {
        setProfileState(null);
      }
    }
    setIsLoaded(true);
  }, []);

  const setProfile = (newProfile: DentistProfile) => {
    localStorage.setItem(PROFILE_KEY, JSON.stringify(newProfile));
    setProfileState(newProfile);
  };

  const clearProfile = () => {
    localStorage.removeItem(PROFILE_KEY);
    setProfileState(null);
  };

  const hasProfile = (): boolean => {
    return profile !== null && profile.name.trim() !== "";
  };

  const getDocumentHeader = (): string => {
    if (!profile) return "";

    return `${profile.name}
${profile.title}
${profile.address}
Tél. : ${profile.phone}
${profile.email}

────────────────────────────────────────`;
  };

  const getDocumentFooter = (): string => {
    return `────────────────────────────────────────
Document généré par assistance IA.
À vérifier et valider avant archivage ou transmission.`;
  };

  return {
    profile,
    setProfile,
    clearProfile,
    hasProfile,
    isLoaded,
    getDocumentHeader,
    getDocumentFooter,
  };
}
