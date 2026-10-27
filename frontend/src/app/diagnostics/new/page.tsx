"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { NewDiagnosisForm } from "@/components/NewDiagnosisForm";
import { listRepositories } from "@/lib/api";
import { Repository } from "@/types/api";

export default function NewDiagnosisPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    listRepositories()
      .then((data) => {
        if (isMounted) {
          setRepositories(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <AppShell>
      <div className="py-4">
        {loading ? (
          <div className="max-w-3xl mx-auto rounded-xl border border-slate-800 bg-[#0d1424] p-12 text-center text-xs text-slate-500">
            Loading repository configurations...
          </div>
        ) : (
          <NewDiagnosisForm existingRepositories={repositories} />
        )}
      </div>
    </AppShell>
  );
}
