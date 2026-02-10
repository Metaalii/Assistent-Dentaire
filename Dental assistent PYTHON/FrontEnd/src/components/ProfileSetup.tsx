import React, { useState } from "react";
import { DentistProfile } from "../hooks/useProfile";
import { useLanguage } from "../i18n";
import { ToothIcon, HeartPulseIcon } from "./ui/Icons";
import { Button } from "./ui";

interface ProfileSetupProps {
  onComplete: (profile: DentistProfile) => void;
}

const ProfileSetup: React.FC<ProfileSetupProps> = ({ onComplete }) => {
  const { t } = useLanguage();
  const [formData, setFormData] = useState<DentistProfile>({
    name: "",
    title: String(t("professionalTitlePlaceholder")),
    address: "",
    phone: "",
    email: "",
  });

  const handleChange = (field: keyof DentistProfile, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.name.trim()) {
      onComplete(formData);
    }
  };

  const isValid = formData.name.trim() !== "";

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#f8fafc] via-[#f0f7fc] to-[#effcfb] dark:from-[#0f172a] dark:via-[#1e293b] dark:to-[#0f172a] relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-gradient-to-br from-[#2d96c6]/20 to-[#28b5ad]/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gradient-to-tr from-[#28b5ad]/20 to-[#2d96c6]/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: "1s" }} />
      </div>

      {/* Main content */}
      <div className="relative z-10 flex flex-col items-center gap-8 p-8 max-w-lg w-full mx-4">
        {/* Logo */}
        <div className="relative">
          <div className="absolute inset-0 w-24 h-24 rounded-full bg-gradient-to-r from-[#2d96c6] to-[#28b5ad] blur-xl opacity-30 animate-pulse" />
          <div className="relative w-24 h-24 rounded-2xl bg-gradient-to-br from-[#2d96c6] to-[#28b5ad] shadow-2xl shadow-[#2d96c6]/30 flex items-center justify-center">
            <ToothIcon className="text-white" size={48} />
          </div>
          <div className="absolute -bottom-1 -right-1 w-8 h-8 rounded-full bg-white dark:bg-[#1e293b] shadow-lg flex items-center justify-center">
            <HeartPulseIcon className="text-[#28b5ad] animate-pulse" size={16} />
          </div>
        </div>

        {/* Title */}
        <div className="text-center">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-[#1e293b] via-[#334155] to-[#1e293b] dark:from-white dark:via-[#94a3b8] dark:to-white bg-clip-text text-transparent">
            {t("profileSetupTitle")}
          </h1>
          <p className="mt-2 text-[#64748b] dark:text-[#94a3b8]">
            {t("profileSetupSubtitle")}
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="w-full space-y-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-[#334155] dark:text-[#e2e8f0] mb-1">
              {t("fullName")} *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => handleChange("name", e.target.value)}
              placeholder={String(t("fullNamePlaceholder"))}
              className="w-full px-4 py-3 rounded-xl border-2 border-[#e2e8f0] dark:border-[#334155] bg-white/80 dark:bg-[#0f172a]/80 text-[#1e293b] dark:text-[#e2e8f0] placeholder-[#94a3b8] dark:placeholder-[#64748b] focus:border-[#2d96c6] focus:ring-2 focus:ring-[#2d96c6]/20 outline-none transition-all"
              required
            />
          </div>

          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-[#334155] dark:text-[#e2e8f0] mb-1">
              {t("professionalTitle")}
            </label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => handleChange("title", e.target.value)}
              placeholder={String(t("professionalTitlePlaceholder"))}
              className="w-full px-4 py-3 rounded-xl border-2 border-[#e2e8f0] dark:border-[#334155] bg-white/80 dark:bg-[#0f172a]/80 text-[#1e293b] dark:text-[#e2e8f0] placeholder-[#94a3b8] dark:placeholder-[#64748b] focus:border-[#2d96c6] focus:ring-2 focus:ring-[#2d96c6]/20 outline-none transition-all"
            />
          </div>

          {/* Address */}
          <div>
            <label className="block text-sm font-medium text-[#334155] dark:text-[#e2e8f0] mb-1">
              {t("officeAddress")}
            </label>
            <input
              type="text"
              value={formData.address}
              onChange={(e) => handleChange("address", e.target.value)}
              placeholder={String(t("officeAddressPlaceholder"))}
              className="w-full px-4 py-3 rounded-xl border-2 border-[#e2e8f0] dark:border-[#334155] bg-white/80 dark:bg-[#0f172a]/80 text-[#1e293b] dark:text-[#e2e8f0] placeholder-[#94a3b8] dark:placeholder-[#64748b] focus:border-[#2d96c6] focus:ring-2 focus:ring-[#2d96c6]/20 outline-none transition-all"
            />
          </div>

          {/* Phone */}
          <div>
            <label className="block text-sm font-medium text-[#334155] dark:text-[#e2e8f0] mb-1">
              {t("phone")}
            </label>
            <input
              type="tel"
              value={formData.phone}
              onChange={(e) => handleChange("phone", e.target.value)}
              placeholder={String(t("phonePlaceholder"))}
              className="w-full px-4 py-3 rounded-xl border-2 border-[#e2e8f0] dark:border-[#334155] bg-white/80 dark:bg-[#0f172a]/80 text-[#1e293b] dark:text-[#e2e8f0] placeholder-[#94a3b8] dark:placeholder-[#64748b] focus:border-[#2d96c6] focus:ring-2 focus:ring-[#2d96c6]/20 outline-none transition-all"
            />
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-[#334155] dark:text-[#e2e8f0] mb-1">
              {t("email")}
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => handleChange("email", e.target.value)}
              placeholder={String(t("emailPlaceholder"))}
              className="w-full px-4 py-3 rounded-xl border-2 border-[#e2e8f0] dark:border-[#334155] bg-white/80 dark:bg-[#0f172a]/80 text-[#1e293b] dark:text-[#e2e8f0] placeholder-[#94a3b8] dark:placeholder-[#64748b] focus:border-[#2d96c6] focus:ring-2 focus:ring-[#2d96c6]/20 outline-none transition-all"
            />
          </div>

          {/* Submit button */}
          <Button
            type="submit"
            variant="primary"
            className="w-full mt-6"
            disabled={!isValid}
          >
            {t("continue")}
          </Button>
        </form>

        {/* Info text */}
        <p className="text-xs text-[#94a3b8] dark:text-[#64748b] text-center">
          {t("profileInfoText")}
        </p>
      </div>
    </div>
  );
};

export default ProfileSetup;
