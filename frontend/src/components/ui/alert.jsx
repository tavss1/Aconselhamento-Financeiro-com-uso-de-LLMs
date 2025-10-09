import React from 'react';

const Alert = React.forwardRef(({ className = "", variant = "default", ...props }, ref) => {
  const baseStyles = "relative w-full rounded-lg border p-4";
  
  const variants = {
    default: "bg-background text-foreground",
    destructive: "border-destructive/50 text-destructive dark:border-destructive [&>svg]:text-destructive",
    warning: "border-yellow-500/50 text-yellow-800 bg-yellow-50 dark:border-yellow-500 [&>svg]:text-yellow-600",
    success: "border-green-500/50 text-green-800 bg-green-50 dark:border-green-500 [&>svg]:text-green-600"
  };

  return (
    <div
      ref={ref}
      role="alert"
      className={`${baseStyles} ${variants[variant]} ${className}`}
      {...props}
    />
  );
});
Alert.displayName = "Alert";

const AlertDescription = React.forwardRef(({ className = "", ...props }, ref) => (
  <div
    ref={ref}
    className={`text-sm [&_p]:leading-relaxed ${className}`}
    {...props}
  />
));
AlertDescription.displayName = "AlertDescription";

const AlertTitle = React.forwardRef(({ className = "", ...props }, ref) => (
  <h5
    ref={ref}
    className={`mb-1 font-medium leading-none tracking-tight ${className}`}
    {...props}
  />
));
AlertTitle.displayName = "AlertTitle";

export { Alert, AlertDescription, AlertTitle };