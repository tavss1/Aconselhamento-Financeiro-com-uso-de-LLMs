import React from 'react';

const Badge = React.forwardRef(({ className = "", variant = "default", ...props }, ref) => {
  const baseStyles = "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2";
  
  const variants = {
    default: "border-transparent bg-blue-600 text-white hover:bg-blue-700",
    secondary: "border-transparent bg-gray-600 text-white hover:bg-gray-700",
    destructive: "border-transparent bg-red-600 text-white hover:bg-red-700",
    outline: "border border-gray-300 text-gray-700 hover:bg-gray-50",
    success: "border-transparent bg-green-600 text-white hover:bg-green-700",
    warning: "border-transparent bg-yellow-600 text-white hover:bg-yellow-700"
  };

  return (
    <div
      ref={ref}
      className={`${baseStyles} ${variants[variant]} ${className}`}
      {...props}
    />
  );
});
Badge.displayName = "Badge";

export { Badge };