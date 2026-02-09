import { useState, useEffect } from "react";

export interface DentistProfile {
  name: string;
  title: string;
  address: string;
  phone: string;
  email: string;
}

const PROFILE_KEY = "dental-assistant-profile";

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

  const getDocumentHeader = (lang: string = "fr"): string => {
    if (!profile) return "";

    const phoneLabel = lang === "fr" ? "Tél." : "Tel.";
    return `${profile.name}
${profile.title}
${profile.address}
${phoneLabel} : ${profile.phone}
${profile.email}

────────────────────────────────────────`;
  };

  const getDocumentFooter = (lang: string = "fr"): string => {
    const disclaimer = lang === "fr"
      ? "Document généré par assistance IA.\nÀ vérifier et valider avant archivage ou transmission."
      : "Document generated with AI assistance.\nPlease verify and validate before archiving or transmission.";
    return `────────────────────────────────────────
${disclaimer}`;
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
