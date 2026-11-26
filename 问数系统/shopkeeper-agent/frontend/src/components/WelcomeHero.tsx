/**
 * 欢迎页（WorkX 式）：时段问候 + 状态 pill + 大输入卡 + 分类推荐卡
 * 空状态时渲染，与底部 bar 形态 Composer 互斥
 */
import {
  ArrowUpRight,
  BarChart3,
  CalendarDays,
  Compass,
  HelpCircle,
  RefreshCw,
  ShoppingBag,
  Trophy,
  Users,
} from "lucide-react";
import { useState } from "react";
import { cn, greeting } from "../lib/format";
import {
  RECOMMEND_GROUPS,
  RECOMMEND_TABS,
  rotate,
  type RecommendCard,
  type RecommendIcon,
} from "../lib/recommend";
import { Composer } from "./Composer";

const TONE_CARD: Record<RecommendCard["tone"], string> = {
  yellow: "bg-pastel-yellow-card",
  purple: "bg-pastel-purple-card",
  pink: "bg-pastel-pink-card",
  blue: "bg-pastel-blue-card",
};

const TONE_ICON: Record<RecommendCard["tone"], string> = {
  yellow: "bg-pastel-yellow-icon text-pastel-yellow-accent",
  purple: "bg-pastel-purple-icon text-pastel-purple-accent",
  pink: "bg-pastel-pink-icon text-pastel-pink-accent",
  blue: "bg-pastel-blue-icon text-pastel-blue-accent",
};

const ICONS: Record<RecommendIcon, typeof BarChart3> = {
  chart: BarChart3,
  bag: ShoppingBag,
  trophy: Trophy,
  users: Users,
  help: HelpCircle,
  compass: Compass,
};

const WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"];

type WelcomeHeroProps = {
  value: string;
  disabled: boolean;
  isStreaming: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onStop: () => void;
  /** 推荐卡点击：直接发起查询 */
  onPick: (question: string) => void;
};

export function WelcomeHero({
  value,
  disabled,
  isStreaming,
  onChange,
  onSubmit,
  onStop,
  onPick,
}: WelcomeHeroProps) {
  const [tab, setTab] = useState<(typeof RECOMMEND_TABS)[number]>(RECOMMEND_TABS[0]);
  const [offset, setOffset] = useState(0);
  const cards = rotate(RECOMMEND_GROUPS[tab], offset);

  const now = new Date();
  const dateLabel = `${now.getMonth() + 1}月${now.getDate()}日 星期${WEEKDAYS[now.getDay()]}`;

  return (
    <div className="mx-auto flex min-h-full max-w-3xl flex-col justify-center px-4 py-10">
      <h1 className="text-4xl font-semibold leading-tight text-ink">
        {greeting()}，想查点什么？
      </h1>

      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-white px-3 py-1 text-secondary">
          <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />
          {dateLabel}
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 font-medium text-brand-600">
          <span className="h-1.5 w-1.5 rounded-full bg-brand-500" aria-hidden="true" />
          服务在线
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 font-medium text-brand-600">
          <span className="h-1.5 w-1.5 rounded-full bg-brand-500" aria-hidden="true" />
          数据已同步
        </span>
      </div>

      <div className="mt-6">
        <Composer
          variant="hero"
          value={value}
          disabled={disabled}
          isStreaming={isStreaming}
          onChange={onChange}
          onSubmit={onSubmit}
          onStop={onStop}
        />
      </div>

      <div className="mt-8 flex items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          {RECOMMEND_TABS.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => {
                setTab(item);
                setOffset(0);
              }}
              className={cn(
                "rounded-full px-4 py-1.5 text-sm font-medium transition",
                item === tab
                  ? "bg-ink text-white"
                  : "bg-surface-muted text-secondary hover:text-ink",
              )}
            >
              {item}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => setOffset((current) => current + 1)}
          className="inline-flex items-center gap-1.5 text-xs text-secondary transition hover:text-ink"
        >
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          换一换
        </button>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => {
          const Icon = ICONS[card.icon];
          return (
            <button
              key={card.id}
              type="button"
              onClick={() => onPick(card.question)}
              className={cn(
                "group rounded-xl p-4 text-left transition hover:-translate-y-0.5 hover:shadow-card",
                TONE_CARD[card.tone],
              )}
            >
              <div className="flex items-start justify-between">
                <div className={cn("grid h-9 w-9 place-items-center rounded-lg", TONE_ICON[card.tone])}>
                  <Icon className="h-4 w-4" aria-hidden="true" />
                </div>
                <ArrowUpRight
                  className="h-4 w-4 text-ink/40 opacity-0 transition group-hover:opacity-100"
                  aria-hidden="true"
                />
              </div>
              <div className="mt-3 text-sm font-semibold text-ink">{card.title}</div>
              <div className="mt-1 text-xs leading-5 text-ink/60">{card.desc}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
