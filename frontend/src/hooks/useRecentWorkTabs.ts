import { useEffect, useMemo, useState } from "react";
import type { Location } from "react-router-dom";
import { ROUTE_PATHS } from "../routes/routePaths";

export type WorkTab = {
  key: string;
  label: string;
  path: string;
  fixed?: boolean;
  lastUsedAt?: number;
};

const STORAGE_KEY = "smartreturn:recent-work-tabs:v1";
const LAST_PATH_STORAGE_KEY = "smartreturn:work-tab-last-paths:v1";
const MAX_RECENT_TABS = 5;

const FIXED_TABS: WorkTab[] = [
  { key: ROUTE_PATHS.dashboard, label: "오늘 작업", path: ROUTE_PATHS.dashboard, fixed: true },
  { key: ROUTE_PATHS.returnProcessing, label: "반품 처리", path: ROUTE_PATHS.returnProcessing, fixed: true },
];

const WORK_TAB_ROUTES: Array<{ pathname: string; label: string; fixed?: boolean }> = [
  { pathname: ROUTE_PATHS.dashboard, label: "오늘 작업", fixed: true },
  { pathname: ROUTE_PATHS.returnProcessing, label: "반품 처리", fixed: true },
  { pathname: ROUTE_PATHS.returnIntake, label: "반품 자료" },
  { pathname: ROUTE_PATHS.returnClosing, label: "반품 마감" },
  { pathname: ROUTE_PATHS.returnExternalOutboundBatches, label: "외부반출 이력" },
  { pathname: ROUTE_PATHS.returnExternalOutbound, label: "반출/폐기" },
  { pathname: ROUTE_PATHS.returnDisposal, label: "폐기관리" },
  { pathname: ROUTE_PATHS.returnHold, label: "보류관리" },
  { pathname: ROUTE_PATHS.returnHistory, label: "반품 이력" },
  { pathname: ROUTE_PATHS.inventoryCurrent, label: "현재고" },
  { pathname: ROUTE_PATHS.inventoryEvents, label: "재고 이벤트" },
  { pathname: ROUTE_PATHS.channelAccounts, label: "채널 연동" },
  { pathname: ROUTE_PATHS.masterClients, label: "고객사 관리" },
  { pathname: ROUTE_PATHS.masterProducts, label: "상품 관리" },
  { pathname: ROUTE_PATHS.masterCommonCodes, label: "공통코드" },
  { pathname: ROUTE_PATHS.importPreview, label: "Smart Import" },
].sort((left, right) => right.pathname.length - left.pathname.length);

export function useRecentWorkTabs(location: Location) {
  const [recentTabs, setRecentTabs] = useState<WorkTab[]>(() => loadRecentTabs());
  const [lastPaths, setLastPaths] = useState<Record<string, string>>(() => loadLastPaths());

  useEffect(() => {
    const route = resolveWorkTabRoute(location.pathname);
    if (!route) {
      return;
    }
    const path = `${location.pathname}${location.search}`;
    setLastPaths((current) => saveLastPaths({ ...current, [route.pathname]: path }));
    if (route.fixed) {
      setRecentTabs((current) => saveRecentTabs(current));
      return;
    }
    setRecentTabs((current) => {
      const nextTab: WorkTab = {
        key: route.pathname,
        label: route.label,
        path,
        lastUsedAt: Date.now(),
      };
      const nextTabs = [nextTab, ...current.filter((tab) => tab.key !== route.pathname)]
        .sort((left, right) => (right.lastUsedAt || 0) - (left.lastUsedAt || 0))
        .slice(0, MAX_RECENT_TABS);
      return saveRecentTabs(nextTabs);
    });
  }, [location.pathname, location.search]);

  const tabs = useMemo(() => {
    return [
      ...FIXED_TABS.map((tab) => ({ ...tab, path: lastPaths[tab.key] || tab.path })),
      ...recentTabs.filter((tab) => !FIXED_TABS.some((fixedTab) => fixedTab.key === tab.key)),
    ];
  }, [lastPaths, recentTabs]);

  function closeRecentTab(key: string) {
    setRecentTabs((current) => saveRecentTabs(current.filter((tab) => tab.key !== key)));
  }

  return { tabs, closeRecentTab };
}

export function resolveWorkTabRoute(pathname: string) {
  return WORK_TAB_ROUTES.find((route) => pathname === route.pathname || pathname.startsWith(`${route.pathname}/`));
}

function loadRecentTabs() {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    const rawValue = window.sessionStorage.getItem(STORAGE_KEY);
    if (!rawValue) {
      return [];
    }
    const parsedValue = JSON.parse(rawValue);
    if (!Array.isArray(parsedValue)) {
      return [];
    }
    return parsedValue
      .filter(isWorkTab)
      .filter((tab) => resolveWorkTabRoute(tab.key) && !FIXED_TABS.some((fixedTab) => fixedTab.key === tab.key))
      .slice(0, MAX_RECENT_TABS);
  } catch {
    return [];
  }
}

function saveRecentTabs(tabs: WorkTab[]) {
  if (typeof window !== "undefined") {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(tabs));
  }
  return tabs;
}

function loadLastPaths() {
  if (typeof window === "undefined") {
    return {};
  }
  try {
    const rawValue = window.sessionStorage.getItem(LAST_PATH_STORAGE_KEY);
    if (!rawValue) {
      return {};
    }
    const parsedValue = JSON.parse(rawValue);
    if (!parsedValue || typeof parsedValue !== "object" || Array.isArray(parsedValue)) {
      return {};
    }
    return Object.fromEntries(
      Object.entries(parsedValue).filter(
        ([key, value]) => typeof key === "string" && typeof value === "string" && resolveWorkTabRoute(key),
      ),
    ) as Record<string, string>;
  } catch {
    return {};
  }
}

function saveLastPaths(paths: Record<string, string>) {
  if (typeof window !== "undefined") {
    window.sessionStorage.setItem(LAST_PATH_STORAGE_KEY, JSON.stringify(paths));
  }
  return paths;
}

function isWorkTab(value: unknown): value is WorkTab {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<WorkTab>;
  return typeof candidate.key === "string" && typeof candidate.label === "string" && typeof candidate.path === "string";
}
