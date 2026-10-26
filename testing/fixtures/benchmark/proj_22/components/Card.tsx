import React from "react";
import { Button } from "./Button";

export const Card: React.FC<{ title: string }> = ({ title }) => {
  return (
    <div className="card">
      <h2>{title}</h2>
      <Button label="Click Me" />
    </div>
  );
};
