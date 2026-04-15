import { useEffect } from "react";
import { useLocation } from "wouter";

/**
 * Home page redirects directly to Lockbox dashboard
 * No landing page or marketing content - direct access to the tool
 */
export default function Home() {
  const [, setLocation] = useLocation();

  useEffect(() => {
    // Redirect immediately to Lockbox
    setLocation("/lockbox");
  }, [setLocation]);

  return null;
}
