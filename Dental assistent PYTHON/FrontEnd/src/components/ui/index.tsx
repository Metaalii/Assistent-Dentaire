import React from "react";

// ============================================
// BUTTON COMPONENT
// ============================================
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
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
    rounded-xl transition-all duration-300 ease-out
    focus:outline-none focus:ring-2 focus:ring-offset-2
    disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none
  `;

  const variants = {
    primary: `
      text-white
      bg-gradient-to-r from-[#35a7d3] to-[#2584ae]
      hover:from-[#2e98c4] hover:to-[#1d7199]
      shadow-lg shadow-[#35a7d3]/30
      hover:shadow-xl hover:shadow-[#35a7d3]/40
      hover:-translate-y-0.5
      focus:ring-[#35a7d3]
    `,
    secondary: `
      text-[#2584ae]
      bg-[#e6f4f9]
      border-2 border-[#c0e4f1]
      hover:bg-[#c0e4f1]
      hover:border-[#98d3e8]
      focus:ring-[#35a7d3]
    `,
    ghost: `
      text-[#64748b]
      bg-transparent
      border border-[#e2e8f0]
      hover:bg-[#f1f5f9]
      hover:border-[#cbd5e1]
      focus:ring-[#64748b]
    `,
    danger: `
      text-white
      bg-gradient-to-r from-[#ef4444] to-[#dc2626]
      hover:from-[#dc2626] hover:to-[#b91c1c]
      shadow-lg shadow-red-500/30
      hover:shadow-xl hover:shadow-red-500/40
      hover:-translate-y-0.5
      focus:ring-red-500
    `,
  };

  const sizes = {
    sm: "px-4 py-2 text-sm",
    md: "px-6 py-3 text-[15px]",
    lg: "px-8 py-4 text-base",
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
      bg-white/85 backdrop-blur-xl
      border border-white/80
      rounded-2xl shadow-lg
    `
    : `
      bg-white
      border border-[#e2e8f0]
      rounded-2xl shadow-md
    `;

  const hoverStyles = hover
    ? "transition-all duration-300 hover:shadow-xl hover:-translate-y-1"
    : "";

  return (
    <div className={`${baseStyles} ${hoverStyles} ${className}`}>
      {children}
    </div>
  );
};

// ============================================
// CARD HEADER COMPONENT
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
      bg-gradient-to-r from-[#f8fafc] to-white
      border-b border-[#f1f5f9]
      rounded-t-2xl
      ${className}
    `}
  >
    {icon && (
      <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-[#35a7d3] to-[#00bdb8] text-white">
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
    md: "w-8 h-8 border-3",
    lg: "w-12 h-12 border-4",
  };

  return (
    <div
      className={`
        ${sizes[size]}
        border-[#e6f4f9]
        border-t-[#35a7d3]
        rounded-full
        animate-spin
        ${className}
      `}
    />
  );
};

// ============================================
// MEDICAL LOADER COMPONENT
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
      <div className="w-16 h-16 rounded-full border-4 border-[#e6f4f9]" />
      {/* Spinning gradient ring */}
      <div
        className="
          absolute inset-0 w-16 h-16
          rounded-full border-4 border-transparent
          border-t-[#35a7d3] border-r-[#00bdb8]
          animate-spin
        "
      />
      {/* Center pulse */}
      <div
        className="
          absolute inset-0 m-auto w-6 h-6
          rounded-full bg-gradient-to-br from-[#35a7d3] to-[#00bdb8]
          animate-pulse
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
            bg-gradient-to-r from-[#35a7d3] to-[#00bdb8]
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
              bg-gradient-to-r from-transparent via-white/40 to-transparent
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
      bg-gradient-to-r from-[#eff6ff] to-[#dbeafe]
      border border-[#bfdbfe]
      text-[#1e40af]
    `,
    success: `
      bg-gradient-to-r from-[#f0fdf4] to-[#dcfce7]
      border border-[#bbf7d0]
      text-[#166534]
    `,
    warning: `
      bg-gradient-to-r from-[#fffbeb] to-[#fef3c7]
      border border-[#fde68a]
      text-[#92400e]
    `,
    error: `
      bg-gradient-to-r from-[#fef2f2] to-[#fee2e2]
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
// ============================================
interface BadgeProps {
  children: React.ReactNode;
  variant?: "primary" | "success" | "warning" | "error" | "neutral";
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "primary",
  className = "",
}) => {
  const variants = {
    primary: "text-[#2584ae] bg-[#e6f4f9]",
    success: "text-[#047857] bg-[#d1fae5]",
    warning: "text-[#b45309] bg-[#fef3c7]",
    error: "text-[#b91c1c] bg-[#fee2e2]",
    neutral: "text-[#475569] bg-[#f1f5f9]",
  };

  return (
    <span
      className={`
        inline-flex items-center gap-1.5
        px-3 py-1
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
