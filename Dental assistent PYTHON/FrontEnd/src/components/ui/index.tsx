import React from "react";

// ============================================
// BUTTON COMPONENT
// Premium dental-themed button with refined styling
// ============================================
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "accent" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = "primary",
  size = "md",
  isLoading = false,
  leftIcon,
  rightIcon,
  className = "",
  disabled,
  ...props
}) => {
  const baseStyles = `
    inline-flex items-center justify-center gap-2 font-semibold
    rounded-xl transition-all duration-200 ease-out
    focus:outline-none focus:ring-2 focus:ring-offset-2
    disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none
  `;

  const variants = {
    primary: `
      text-white
      bg-gradient-to-br from-[#2d96c6] to-[#1e7aa8]
      hover:from-[#1e7aa8] hover:to-[#1a6289]
      shadow-[0_4px_14px_rgba(45,150,198,0.25)]
      hover:shadow-[0_8px_25px_rgba(45,150,198,0.3)]
      hover:-translate-y-0.5
      focus:ring-[#52b1db]
      active:translate-y-0
    `,
    secondary: `
      text-[#1a6289]
      bg-[#f0f7fc]
      border-[1.5px] border-[#bde0f3]
      hover:bg-[#e1f0f9]
      hover:border-[#8acae9]
      hover:text-[#1a5271]
      focus:ring-[#8acae9]
    `,
    accent: `
      text-white
      bg-gradient-to-br from-[#28b5ad] to-[#1f9290]
      hover:from-[#1f9290] hover:to-[#1e7574]
      shadow-[0_4px_14px_rgba(40,181,173,0.25)]
      hover:shadow-[0_8px_25px_rgba(40,181,173,0.3)]
      hover:-translate-y-0.5
      focus:ring-[#43cec6]
      active:translate-y-0
    `,
    ghost: `
      text-[#475569]
      bg-transparent
      border-[1.5px] border-[#e2e8f0]
      hover:bg-[#f8fafc]
      hover:border-[#cbd5e1]
      hover:text-[#334155]
      focus:ring-[#94a3b8]
    `,
    danger: `
      text-white
      bg-gradient-to-br from-[#ef4444] to-[#dc2626]
      hover:from-[#dc2626] hover:to-[#b91c1c]
      shadow-[0_4px_14px_rgba(239,68,68,0.25)]
      hover:shadow-[0_8px_25px_rgba(239,68,68,0.3)]
      hover:-translate-y-0.5
      focus:ring-[#f87171]
      active:translate-y-0
    `,
  };

  const sizes = {
    sm: "px-4 py-2 text-sm",
    md: "px-5 py-2.5 text-[15px]",
    lg: "px-6 py-3 text-base",
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <LoadingSpinner size="sm" />
      ) : (
        <>
          {leftIcon && <span className="flex-shrink-0">{leftIcon}</span>}
          {children}
          {rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
        </>
      )}
    </button>
  );
};

// ============================================
// CARD COMPONENT
// Clean, professional card with subtle styling
// ============================================
interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  glass?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = "",
  hover = false,
  glass = false,
}) => {
  const baseStyles = glass
    ? `
      bg-white/90 backdrop-blur-xl
      border border-white/80
      rounded-2xl shadow-md
    `
    : `
      bg-white
      border border-[#e2e8f0]
      rounded-2xl shadow-sm
    `;

  const hoverStyles = hover
    ? "transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 hover:border-[#bde0f3]"
    : "";

  return (
    <div className={`${baseStyles} ${hoverStyles} ${className}`}>
      {children}
    </div>
  );
};

// ============================================
// CARD HEADER COMPONENT
// Refined header with gradient accent
// ============================================
interface CardHeaderProps {
  children: React.ReactNode;
  className?: string;
  icon?: React.ReactNode;
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  children,
  className = "",
  icon,
}) => (
  <div
    className={`
      flex items-center gap-3 px-5 py-4
      bg-gradient-to-r from-[#f8fafc]/80 to-white
      border-b border-[#f1f5f9]
      rounded-t-2xl
      ${className}
    `}
  >
    {icon && (
      <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-[#2d96c6] to-[#28b5ad] text-white shadow-[0_4px_14px_rgba(45,150,198,0.25)]">
        {icon}
      </div>
    )}
    <div className="flex-1">{children}</div>
  </div>
);

// ============================================
// CARD BODY COMPONENT
// ============================================
interface CardBodyProps {
  children: React.ReactNode;
  className?: string;
}

export const CardBody: React.FC<CardBodyProps> = ({ children, className = "" }) => (
  <div className={`p-5 ${className}`}>{children}</div>
);

// ============================================
// LOADING SPINNER COMPONENT
// Refined dental-themed spinner
// ============================================
interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = "md",
  className = "",
}) => {
  const sizes = {
    sm: "w-4 h-4 border-2",
    md: "w-8 h-8 border-[3px]",
    lg: "w-12 h-12 border-4",
  };

  return (
    <div
      className={`
        ${sizes[size]}
        border-[#e1f0f9]
        border-t-[#2d96c6]
        rounded-full
        animate-spin
        ${className}
      `}
    />
  );
};

// ============================================
// MEDICAL LOADER COMPONENT
// Premium double-ring loader with pulsing center
// ============================================
interface MedicalLoaderProps {
  text?: string;
  className?: string;
}

export const MedicalLoader: React.FC<MedicalLoaderProps> = ({
  text,
  className = "",
}) => (
  <div className={`flex flex-col items-center gap-4 ${className}`}>
    <div className="relative">
      {/* Outer ring */}
      <div className="w-16 h-16 rounded-full border-[3px] border-[#e1f0f9]" />
      {/* Spinning gradient ring */}
      <div
        className="
          absolute inset-0 w-16 h-16
          rounded-full border-[3px] border-transparent
          border-t-[#2d96c6] border-r-[#28b5ad]
          animate-spin
        "
      />
      {/* Center pulse */}
      <div
        className="
          absolute inset-0 m-auto w-6 h-6
          rounded-full bg-gradient-to-br from-[#2d96c6] to-[#28b5ad]
          animate-pulse shadow-[0_0_20px_rgba(45,150,198,0.2)]
        "
      />
    </div>
    {text && (
      <p className="text-[#64748b] font-medium animate-pulse">{text}</p>
    )}
  </div>
);

// ============================================
// PROGRESS BAR COMPONENT
// Refined progress bar with shimmer effect
// ============================================
interface ProgressBarProps {
  value: number;
  max?: number;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  showLabel = false,
  size = "md",
  className = "",
}) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  const sizes = {
    sm: "h-1.5",
    md: "h-2.5",
    lg: "h-4",
  };

  return (
    <div className={`w-full ${className}`}>
      <div
        className={`
          w-full ${sizes[size]}
          bg-[#f1f5f9]
          rounded-full
          overflow-hidden
        `}
      >
        <div
          className={`
            ${sizes[size]}
            bg-gradient-to-r from-[#2d96c6] to-[#28b5ad]
            rounded-full
            transition-all duration-500 ease-out
            relative
          `}
          style={{ width: `${percentage}%` }}
        >
          {/* Shimmer effect */}
          <div
            className="
              absolute inset-0
              bg-gradient-to-r from-transparent via-white/30 to-transparent
              animate-[shimmer_2s_infinite]
            "
          />
        </div>
      </div>
      {showLabel && (
        <div className="mt-2 text-sm text-[#64748b] font-medium text-right">
          {Math.round(percentage)}%
        </div>
      )}
    </div>
  );
};

// ============================================
// ALERT COMPONENT
// Professional alert with gradient background
// ============================================
interface AlertProps {
  children: React.ReactNode;
  variant?: "info" | "success" | "warning" | "error";
  icon?: React.ReactNode;
  className?: string;
}

export const Alert: React.FC<AlertProps> = ({
  children,
  variant = "info",
  icon,
  className = "",
}) => {
  const variants = {
    info: `
      bg-gradient-to-r from-[#eff6ff] to-[#eff6ff]/50
      border border-[#bfdbfe]
      text-[#1e40af]
    `,
    success: `
      bg-gradient-to-r from-[#ecfdf5] to-[#ecfdf5]/50
      border border-[#a7f3d0]
      text-[#166534]
    `,
    warning: `
      bg-gradient-to-r from-[#fffbeb] to-[#fffbeb]/50
      border border-[#fde68a]
      text-[#92400e]
    `,
    error: `
      bg-gradient-to-r from-[#fef2f2] to-[#fef2f2]/50
      border border-[#fecaca]
      text-[#991b1b]
    `,
  };

  return (
    <div
      className={`
        flex items-start gap-3
        p-4 rounded-xl
        ${variants[variant]}
        ${className}
      `}
    >
      {icon && <span className="flex-shrink-0 mt-0.5">{icon}</span>}
      <div className="flex-1">{children}</div>
    </div>
  );
};

// ============================================
// BADGE COMPONENT
// Clean badge with refined colors
// ============================================
interface BadgeProps {
  children: React.ReactNode;
  variant?: "primary" | "accent" | "success" | "warning" | "error" | "neutral";
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "primary",
  className = "",
}) => {
  const variants = {
    primary: "text-[#1a6289] bg-[#e1f0f9]",
    accent: "text-[#1e7574] bg-[#d7f7f5]",
    success: "text-[#166534] bg-[#dcfce7]",
    warning: "text-[#92400e] bg-[#fef3c7]",
    error: "text-[#991b1b] bg-[#fee2e2]",
    neutral: "text-[#475569] bg-[#f1f5f9]",
  };

  return (
    <span
      className={`
        inline-flex items-center gap-1.5
        px-2.5 py-1
        text-xs font-semibold
        rounded-full
        ${variants[variant]}
        ${className}
      `}
    >
      {children}
    </span>
  );
};

// ============================================
// DIVIDER COMPONENT
// ============================================
interface DividerProps {
  className?: string;
}

export const Divider: React.FC<DividerProps> = ({ className = "" }) => (
  <hr className={`border-t border-[#e2e8f0] ${className}`} />
);

// ============================================
// SKELETON COMPONENT
// Loading placeholder with shimmer
// ============================================
interface SkeletonProps {
  className?: string;
  variant?: "text" | "circular" | "rectangular";
  width?: string | number;
  height?: string | number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = "",
  variant = "text",
  width,
  height,
}) => {
  const variants = {
    text: "h-4 rounded",
    circular: "rounded-full",
    rectangular: "rounded-xl",
  };

  return (
    <div
      className={`
        bg-gradient-to-r from-[#f1f5f9] via-[#e2e8f0] to-[#f1f5f9]
        bg-[length:200%_100%]
        animate-[shimmer_1.5s_infinite]
        ${variants[variant]}
        ${className}
      `}
      style={{ width, height }}
    />
  );
};

// ============================================
// CONTAINER COMPONENT
// Responsive container with refined sizing
// ============================================
interface ContainerProps {
  children: React.ReactNode;
  className?: string;
  size?: "sm" | "md" | "lg" | "xl" | "full";
}

export const Container: React.FC<ContainerProps> = ({
  children,
  className = "",
  size = "lg",
}) => {
  const sizes = {
    sm: "max-w-2xl",
    md: "max-w-4xl",
    lg: "max-w-6xl",
    xl: "max-w-7xl",
    full: "max-w-full",
  };

  return (
    <div className={`mx-auto px-4 sm:px-6 lg:px-8 ${sizes[size]} ${className}`}>
      {children}
    </div>
  );
};

// ============================================
// TOOLTIP COMPONENT
// Simple tooltip for additional context
// ============================================
interface TooltipProps {
  children: React.ReactNode;
  content: string;
  className?: string;
}

export const Tooltip: React.FC<TooltipProps> = ({
  children,
  content,
  className = "",
}) => (
  <div className={`group relative inline-block ${className}`}>
    {children}
    <div
      className="
        absolute bottom-full left-1/2 -translate-x-1/2 mb-2
        px-3 py-1.5 rounded-lg
        bg-[#1e293b] text-white text-xs font-medium
        opacity-0 invisible group-hover:opacity-100 group-hover:visible
        transition-all duration-200
        whitespace-nowrap
        shadow-lg
        z-50
      "
    >
      {content}
      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-[#1e293b]" />
    </div>
  </div>
);

// ============================================
// INPUT COMPONENT
// Styled input field for forms
// ============================================
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  className = "",
  ...props
}) => (
  <div className="w-full">
    {label && (
      <label className="block text-sm font-medium text-[#334155] mb-1.5">
        {label}
      </label>
    )}
    <input
      className={`
        w-full px-4 py-2.5
        rounded-xl
        border-[1.5px] ${error ? 'border-red-300' : 'border-[#e2e8f0]'}
        bg-white
        text-[#1e293b] placeholder-[#94a3b8]
        focus:border-[#52b1db] focus:ring-2 focus:ring-[#f0f7fc]
        outline-none transition-all duration-200
        ${className}
      `}
      {...props}
    />
    {error && (
      <p className="mt-1.5 text-sm text-red-600">{error}</p>
    )}
  </div>
);

// ============================================
// ICON BUTTON COMPONENT
// Compact button for icon-only actions
// ============================================
interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "primary" | "danger";
  size?: "sm" | "md" | "lg";
}

export const IconButton: React.FC<IconButtonProps> = ({
  children,
  variant = "default",
  size = "md",
  className = "",
  ...props
}) => {
  const variants = {
    default: "text-[#64748b] hover:text-[#2d96c6] hover:bg-[#f0f7fc]",
    primary: "text-[#2d96c6] hover:text-[#1e7aa8] hover:bg-[#e1f0f9]",
    danger: "text-[#ef4444] hover:text-[#dc2626] hover:bg-[#fef2f2]",
  };

  const sizes = {
    sm: "w-8 h-8",
    md: "w-10 h-10",
    lg: "w-12 h-12",
  };

  return (
    <button
      className={`
        inline-flex items-center justify-center
        rounded-xl
        transition-all duration-200
        focus:outline-none focus:ring-2 focus:ring-[#bde0f3]
        ${variants[variant]}
        ${sizes[size]}
        ${className}
      `}
      {...props}
    >
      {children}
    </button>
  );
};
