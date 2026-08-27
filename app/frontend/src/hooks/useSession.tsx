import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { Employee, queryAll } from '@/lib/api';

interface SessionValue {
  employees: Employee[];
  actor: Employee | null;
  loading: boolean;
  setActorEmpNo: (empNo: string) => void;
  reload: () => Promise<void>;
}

const SessionContext = createContext<SessionValue>({
  employees: [],
  actor: null,
  loading: true,
  setActorEmpNo: () => undefined,
  reload: async () => undefined,
});

const STORAGE_KEY = 'timeledger.actor';

export function SessionProvider({ children }: { children: ReactNode }) {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [actorEmpNo, setActorEmpNoState] = useState<string>(() => localStorage.getItem(STORAGE_KEY) ?? '');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await queryAll<Employee>('employees', { sort: 'emp_no', limit: 200 });
      setEmployees(rows);
      setActorEmpNoState((prev) => {
        if (prev && rows.some((r) => r.emp_no === prev)) return prev;
        const hr = rows.find((r) => r.role === 'hr') ?? rows[0];
        return hr?.emp_no ?? '';
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const setActorEmpNo = useCallback((empNo: string) => {
    localStorage.setItem(STORAGE_KEY, empNo);
    setActorEmpNoState(empNo);
  }, []);

  const value = useMemo<SessionValue>(
    () => ({
      employees,
      actor: employees.find((e) => e.emp_no === actorEmpNo) ?? null,
      loading,
      setActorEmpNo,
      reload: load,
    }),
    [employees, actorEmpNo, loading, setActorEmpNo, load],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionValue {
  return useContext(SessionContext);
}