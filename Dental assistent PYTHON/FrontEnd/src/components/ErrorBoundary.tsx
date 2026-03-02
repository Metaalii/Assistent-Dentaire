import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AppError } from '../errors';
import { AlertCircleIcon, RefreshIcon } from './ui/Icons';
import { Button } from './ui';
import { useLanguage } from '../i18n';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

// Functional component for the error UI — can use hooks.
interface ErrorFallbackProps {
  error: Error | null;
  onRetry: () => void;
  onReload: () => void;
}

const ErrorFallback: React.FC<ErrorFallbackProps> = ({ error, onRetry, onReload }) => {
  const { t } = useLanguage();
  return (
    <div className="min-h-[400px] flex items-center justify-center p-8">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-red-100 p-8 text-center">
        <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-red-500 to-red-600 shadow-lg shadow-red-500/30 flex items-center justify-center mb-6">
          <AlertCircleIcon className="text-white" size={32} />
        </div>
        <h2 className="text-xl font-bold text-[#1e293b] mb-3">
          {String(t("errorBoundaryTitle"))}
        </h2>
        <p className="text-[#64748b] mb-6">
          {String(t("errorBoundaryMessage"))}
        </p>
        {error && (
          <details className="mb-6 text-left">
            <summary className="cursor-pointer text-sm text-[#94a3b8] hover:text-[#64748b]">
              {String(t("technicalDetails"))}
            </summary>
            <div className="mt-2 p-3 bg-red-50 dark:bg-red-950/50 rounded-lg border border-red-100 dark:border-red-900/50 overflow-auto max-h-40">
              {error instanceof AppError && (
                <p className="text-xs font-mono text-red-600 dark:text-red-400 mb-1">
                  Code: {(error as AppError).code}
                  {(error as AppError).requestId &&
                    ` | Request: ${(error as AppError).requestId}`}
                </p>
              )}
              <code className="text-xs text-red-700 dark:text-red-300 whitespace-pre-wrap break-all">
                {error instanceof AppError
                  ? (error as AppError).toDebugString()
                  : error.message}
              </code>
            </div>
          </details>
        )}
        <div className="flex gap-3 justify-center">
          <Button variant="primary" onClick={onRetry} leftIcon={<RefreshIcon size={16} />}>
            {String(t("tryAgain"))}
          </Button>
          <Button variant="secondary" onClick={onReload}>
            {String(t("reloadPage"))}
          </Button>
        </div>
      </div>
    </div>
  );
};

/**
 * Error Boundary component for catching and displaying React errors gracefully.
 * Prevents the entire app from crashing when a component throws an error.
 */
class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });

    // Log structured error info for debugging
    if (error instanceof AppError) {
      console.error(
        `[ErrorBoundary] ${error.toDebugString()}`,
        errorInfo,
      );
    } else {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    // Call custom error handler if provided
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  handleReload = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // Custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI — rendered via functional component so it can use hooks.
      return (
        <ErrorFallback
          error={this.state.error}
          onRetry={this.handleRetry}
          onReload={this.handleReload}
        />
      );
    }

    return this.props.children;
  }
}

/**
 * HOC to wrap a component with ErrorBoundary
 */
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  fallback?: ReactNode
): React.FC<P> {
  const displayName = WrappedComponent.displayName || WrappedComponent.name || 'Component';

  const ComponentWithBoundary: React.FC<P> = (props) => (
    <ErrorBoundary fallback={fallback}>
      <WrappedComponent {...props} />
    </ErrorBoundary>
  );

  ComponentWithBoundary.displayName = `withErrorBoundary(${displayName})`;
  return ComponentWithBoundary;
}

export default ErrorBoundary;
