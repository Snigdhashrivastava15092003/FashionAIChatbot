"use client";

import { useEffect, useEffectEvent, useRef, useState, startTransition } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight,
  Bot,
  CircleAlert,
  Loader2,
  Send,
  Sparkles,
  Star,
  TrendingUp,
  User,
  Zap,
} from "lucide-react";

import styles from "../page.module.css";

type Role = "user" | "assistant";

type Message = {
  role: Role;
  content: string;
};

type Recommendation = {
  outfit_title: string;
  overview: string;
  clothing_items: string[];
  colors: string[];
  accessories: string[];
  footwear: string[];
  style_tips: string[];
  budget_fit: string;
  occasion_match_reason: string;
};

type Trend = {
  name: string;
  highlight: string;
  source: string;
};

type ApiResponse = {
  reply: string;
  recommendation: Recommendation;
  trends: Trend[];
  source: "rule-based" | "hybrid" | "llm";
  warnings: string[];
};

type HealthState = {
  status: "checking" | "online" | "degraded" | "offline";
  message: string;
};

type StyleOption =
  | "Minimal"
  | "Classic"
  | "Streetwear"
  | "Romantic"
  | "Edgy"
  | "Casual";

type ProfileState = {
  personality: string;
  budget: string;
  occasion: string;
  style_preferences: StyleOption[];
};

const STORAGE_KEY = "fashion-ai-studio-state";
const QUICK_PROMPTS = ["Beach Wedding", "Business Casual", "First Date", "Winter Streetwear"] as const;
const STYLE_OPTIONS: StyleOption[] = ["Minimal", "Classic", "Streetwear", "Romantic", "Edgy", "Casual"];
const TRENDING_LOOKS = ["Neo Tailoring", "Soft Metallics", "Quiet Luxury", "Utility Romance"];
const OCCASION_TAGS = ["Work Edit", "Vacation", "Date Night", "Wedding Guest"];

const defaultRecommendation: Recommendation = {
  outfit_title: "Your next signature look starts here",
  overview:
    "Tell Fashion AI about your occasion, budget, and style personality to receive a structured outfit direction.",
  clothing_items: ["Tailored outer layer", "Refined top", "Versatile bottom"],
  colors: ["soft silver", "ink black", "neon pink accent"],
  accessories: ["Statement accessory", "Structured bag", "Layering piece"],
  footwear: ["Polished boots or elevated sneakers"],
  style_tips: [
    "Start with one hero piece, then keep the rest balanced and editorial.",
    "Use your budget on the item that defines the silhouette.",
  ],
  budget_fit: "Recommendations adapt from affordable wardrobe refreshes to premium investment pieces.",
  occasion_match_reason: "The outfit will be tuned to your event, personal energy, and preferred style direction.",
};

const initialMessages: Message[] = [
  {
    role: "assistant",
    content:
      "Share your occasion, budget, and personal style. I'll shape it into a polished AI-styled fashion direction.",
  },
];

const defaultProfile: ProfileState = {
  personality: "Polished",
  budget: "Mid-range",
  occasion: "Fashion networking event",
  style_preferences: ["Minimal", "Classic"],
};

function inferPromptDetails(prompt: string): Partial<ProfileState> {
  const normalized = prompt.toLowerCase();
  if (normalized.includes("beach wedding")) {
    return { occasion: "Beach wedding", style_preferences: ["Romantic", "Classic"] };
  }
  if (normalized.includes("business casual")) {
    return { occasion: "Business casual", style_preferences: ["Minimal", "Classic"] };
  }
  if (normalized.includes("first date")) {
    return { occasion: "First date", style_preferences: ["Romantic", "Edgy"] };
  }
  if (normalized.includes("winter streetwear")) {
    return { occasion: "Winter streetwear", style_preferences: ["Streetwear", "Edgy"] };
  }
  return {};
}

export default function FashionStudio() {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [profile, setProfile] = useState<ProfileState>(defaultProfile);
  const [latest, setLatest] = useState<ApiResponse | null>(null);
  const [hasHydrated, setHasHydrated] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthState>({
    status: "checking",
    message: "Connecting stylist engine",
  });
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = useEffectEvent(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  });

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (!saved) {
        return;
      }

      const parsed = JSON.parse(saved) as {
        messages?: Message[];
        latest?: ApiResponse | null;
        profile?: ProfileState;
      };

      if (parsed.messages?.length) {
        setMessages(parsed.messages);
      }
      if (parsed.latest) {
        setLatest(parsed.latest);
      }
      if (parsed.profile) {
        setProfile(parsed.profile);
      }
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    } finally {
      setHasHydrated(true);
    }
  }, []);

  useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        messages,
        latest,
        profile,
      }),
    );
    scrollToBottom();
  }, [hasHydrated, latest, messages, profile]);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch("/api/python/health", { cache: "no-store" });
        if (!response.ok) {
          throw new Error("Health check failed");
        }

        const data = (await response.json()) as { llm_enabled?: boolean };
        setHealth({
          status: data.llm_enabled ? "online" : "degraded",
          message: data.llm_enabled ? "AI stylist online" : "Fallback stylist online",
        });
      } catch {
        setHealth({
          status: "offline",
          message: "Backend offline",
        });
      }
    };

    checkHealth();
  }, []);

  const handleStyleToggle = (style: StyleOption) => {
    setProfile((current) => {
      const exists = current.style_preferences.includes(style);
      const style_preferences = exists
        ? current.style_preferences.filter((item) => item !== style)
        : [...current.style_preferences, style].slice(-4);

      return {
        ...current,
        style_preferences,
      };
    });
  };

  const handleQuickPrompt = (prompt: string) => {
    const promptDetails = inferPromptDetails(prompt);
    setInput(`Build a polished outfit for ${prompt} with a ${profile.budget.toLowerCase()} budget.`);
    setProfile((current) => ({
      ...current,
      ...promptDetails,
    }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) {
      return;
    }

    const userMessage: Message = { role: "user", content: trimmed };
    const nextMessages = [...messages, userMessage];

    startTransition(() => {
      setMessages(nextMessages);
      setInput("");
      setErrorMessage(null);
      setIsLoading(true);
    });

    try {
      const response = await fetch("/api/python/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: trimmed,
          history: messages,
          ...profile,
        }),
      });

      const raw = await response.text();
      const payload = raw ? (JSON.parse(raw) as Partial<ApiResponse> & { detail?: string }) : {};
      if (!response.ok) {
        throw new Error(payload.detail ?? "The stylist request failed.");
      }

      const data = payload as ApiResponse;
      startTransition(() => {
        setLatest(data);
        setMessages((current) => [...current, { role: "assistant", content: data.reply }]);
        setHealth((current) => ({
          ...current,
          status: data.source === "hybrid" ? "online" : "degraded",
          message: data.source === "hybrid" ? "AI stylist online" : "Fallback stylist online",
        }));
      });
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Unknown error";
      startTransition(() => {
        setErrorMessage(detail);
        setMessages((current) => [
          ...current,
          {
            role: "assistant",
            content: "I couldn't complete that request cleanly. Adjust your brief or try again in a moment.",
          },
        ]);
      });
    } finally {
      setIsLoading(false);
    }
  };

  const recommendation = latest?.recommendation ?? defaultRecommendation;
  const trends = latest?.trends ?? [];

  return (
    <div className={styles.pageShell}>
      <div className={styles.glowOrb} />
      <header className={styles.navbar}>
        <div className={styles.brandLockup}>
          <span className={styles.brandPill}>Fashion AI</span>
          <p className={styles.brandCaption}>Editorial styling intelligence</p>
        </div>

        <nav className={styles.navLinks} aria-label="Primary">
          <a href="#home">Home</a>
          <a href="#recommendations">Recommendations</a>
          <a href="#trends">Trends</a>
          <a href="#styling">Styling</a>
        </nav>

        <div className={`${styles.healthBadge} ${styles[health.status]}`}>
          <span className={styles.healthDot} />
          {health.message}
        </div>
      </header>

      <main className={styles.mainLayout}>
        <section className={styles.heroSection} id="home">
          <div className={styles.heroLeft}>
            <div className={styles.heroTagRow}>
              <span className={styles.heroTag}>Future of personal styling</span>
              <span className={styles.heroTagMuted}>AI-powered fashion direction</span>
            </div>

            <div className={styles.heroHeadline}>
              <span className={styles.heroAi}>AI</span>
              <span className={styles.heroIn}>in</span>
              <span className={styles.heroFashion}>Fashion</span>
            </div>

            <p className={styles.heroDescription}>
              A premium fashion-tech studio for outfit recommendations, trend-aware styling, and occasion-led edits
              tailored to your personality and budget.
            </p>

            <div className={styles.heroButtons}>
              <button
                type="button"
                className={styles.ctaPrimary}
                onClick={() =>
                  setInput("Create an editorial AI-styled outfit for a fashion event with a polished personality.")
                }
              >
                Start AI Styling
                <ArrowRight size={18} />
              </button>
              <button type="button" className={styles.ctaSecondary} onClick={() => handleQuickPrompt("First Date")}>
                Explore Trends
              </button>
            </div>

            <div className={styles.heroInfoGrid}>
              <article className={styles.infoCard}>
                <Sparkles size={18} />
                <div>
                  <strong>AI outfit recommendations</strong>
                  <p>Structured styling with clothing, color, accessories, and occasion fit.</p>
                </div>
              </article>
              <article className={styles.infoCard}>
                <TrendingUp size={18} />
                <div>
                  <strong>Trend-informed looks</strong>
                  <p>Editorial cues and current signals blended into practical recommendations.</p>
                </div>
              </article>
            </div>
          </div>

          <div className={styles.heroRight}>
            <div className={styles.visualCard}>
              <div className={styles.visualBadge}>Luxury AI fashion direction</div>
              <div className={styles.modelStage}>
                <div className={styles.modelGlow} />
                <div className={styles.modelFigure}>
                  <span className={styles.figureHead} />
                  <span className={styles.figureBody} />
                </div>
                <div className={styles.floatingCardTop}>
                  <span>Trending Look</span>
                  <strong>Neo Tailoring</strong>
                </div>
                <div className={styles.floatingCardBottom}>
                  <span>Style Mood</span>
                  <strong>Silver minimalism</strong>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className={styles.editorialStrip}>
          <article className={styles.editorialCard}>
            <Zap size={18} />
            <h3>Personalized styling</h3>
            <p>Recommendations adapt to occasion, budget, and personality in one concise flow.</p>
          </article>
          <article className={styles.editorialCard}>
            <Star size={18} />
            <h3>Trending looks</h3>
            <p>Premium trend context keeps the output current without sacrificing wearability.</p>
          </article>
          <article className={styles.editorialCard}>
            <Bot size={18} />
            <h3>Occasion intelligence</h3>
            <p>From work edits to weddings, the assistant maps styling to real-life context.</p>
          </article>
        </section>

        <section className={styles.featureGrid}>
          <div className={styles.featurePanel}>
            <p className={styles.sectionLabel}>Trending looks</p>
            <div className={styles.miniChipRow}>
              {TRENDING_LOOKS.map((look) => (
                <span key={look} className={styles.miniChip}>
                  {look}
                </span>
              ))}
            </div>
          </div>

          <div className={styles.featurePanel}>
            <p className={styles.sectionLabel}>Occasion categories</p>
            <div className={styles.miniChipRow}>
              {OCCASION_TAGS.map((tag) => (
                <span key={tag} className={styles.miniChip}>
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </section>

        <section className={styles.workspaceSection} id="styling">
          <div className={styles.stylingPanel}>
            <div className={styles.panelHeader}>
              <div>
                <p className={styles.sectionLabel}>Personalized styling</p>
                <h2>Build your brief</h2>
              </div>
              <div className={styles.panelMode}>
                <Bot size={16} />
                {latest?.source ?? "ready"}
              </div>
            </div>

            <div className={styles.profileCard}>
              <div className={styles.profileGrid}>
                <label>
                  Personality
                  <input
                    value={profile.personality}
                    onChange={(event) =>
                      setProfile((current) => ({ ...current, personality: event.target.value }))
                    }
                    placeholder="Polished, bold, creative"
                  />
                </label>
                <label>
                  Budget
                  <input
                    value={profile.budget}
                    onChange={(event) => setProfile((current) => ({ ...current, budget: event.target.value }))}
                    placeholder="Budget, mid-range, luxury"
                  />
                </label>
                <label className={styles.fullField}>
                  Occasion
                  <input
                    value={profile.occasion}
                    onChange={(event) => setProfile((current) => ({ ...current, occasion: event.target.value }))}
                    placeholder="Gallery launch, beach wedding, first date"
                  />
                </label>
              </div>

              <div className={styles.preferenceBlock}>
                <p>Style preferences</p>
                <div className={styles.chipRow}>
                  {STYLE_OPTIONS.map((style) => (
                    <button
                      key={style}
                      type="button"
                      onClick={() => handleStyleToggle(style)}
                      className={
                        profile.style_preferences.includes(style)
                          ? `${styles.choiceChip} ${styles.choiceChipActive}`
                          : styles.choiceChip
                      }
                    >
                      {style}
                    </button>
                  ))}
                </div>
              </div>

              <div className={styles.preferenceBlock}>
                <p>Quick prompts</p>
                <div className={styles.quickPromptGrid}>
                  {QUICK_PROMPTS.map((prompt) => (
                    <button key={prompt} type="button" onClick={() => handleQuickPrompt(prompt)}>
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className={styles.chatShell}>
              <div className={styles.chatMessages}>
                <AnimatePresence initial={false}>
                  {messages.map((message, index) => (
                    <motion.div
                      key={`${message.role}-${index}`}
                      initial={{ opacity: 0, y: 16 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.25, ease: "easeOut" }}
                      className={
                        message.role === "user"
                          ? `${styles.messageRow} ${styles.messageRowUser}`
                          : styles.messageRow
                      }
                    >
                      <div className={styles.messageAvatar}>
                        {message.role === "user" ? <User size={16} /> : <Bot size={16} />}
                      </div>
                      <div
                        className={
                          message.role === "user"
                            ? `${styles.messageBubble} ${styles.userBubble}`
                            : `${styles.messageBubble} ${styles.assistantBubble}`
                        }
                      >
                        {message.content}
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>

                {isLoading ? (
                  <div className={styles.loadingRow}>
                    <div className={styles.messageAvatar}>
                      <Bot size={16} />
                    </div>
                    <div className={styles.loadingBubble}>
                      <Loader2 size={16} className={styles.spinner} />
                      Generating your editorial outfit...
                    </div>
                  </div>
                ) : null}
                <div ref={messagesEndRef} />
              </div>

              <form className={styles.composer} onSubmit={handleSubmit}>
                <label>
                  Styling prompt
                  <textarea
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    placeholder="Describe the look you want. Include the occasion, budget, and desired vibe."
                    rows={4}
                  />
                </label>

                <div className={styles.composerActions}>
                  <p>Ask for trend-forward looks, refined capsule edits, or occasion-based outfits.</p>
                  <button className={styles.ctaPrimary} type="submit" disabled={isLoading}>
                    {isLoading ? "Working..." : "Get Styled"}
                    <Send size={18} />
                  </button>
                </div>
              </form>

              {errorMessage ? (
                <div className={styles.errorState}>
                  <CircleAlert size={18} />
                  <span>{errorMessage}</span>
                </div>
              ) : null}
            </div>
          </div>

          <aside className={styles.resultsPanel} id="recommendations">
            <div className={styles.panelHeader}>
              <div>
                <p className={styles.sectionLabel}>AI outfit recommendations</p>
                <h2>{recommendation.outfit_title}</h2>
              </div>
              <span className={styles.sourcePill}>{latest?.source ?? "preview"}</span>
            </div>

            <p className={styles.recommendationText}>{recommendation.overview}</p>

            <div className={styles.recommendationGrid}>
              <article className={styles.recommendationCard}>
                <h3>Outfit Pieces</h3>
                <ul>
                  {recommendation.clothing_items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>

              <article className={styles.recommendationCard}>
                <h3>Accessories</h3>
                <ul>
                  {recommendation.accessories.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>

              <article className={styles.recommendationCard}>
                <h3>Footwear</h3>
                <ul>
                  {recommendation.footwear.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>

              <article className={styles.recommendationCard}>
                <h3>Color Story</h3>
                <div className={styles.colorTokens}>
                  {recommendation.colors.map((color) => (
                    <span key={color}>{color}</span>
                  ))}
                </div>
              </article>
            </div>

            <div className={styles.summaryStrip}>
              <div>
                <strong>Budget</strong>
                <span>{recommendation.budget_fit}</span>
              </div>
              <div>
                <strong>Occasion</strong>
                <span>{recommendation.occasion_match_reason}</span>
              </div>
            </div>

            <article className={styles.tipsCard}>
              <h3>Style vibe</h3>
              <ul>
                {recommendation.style_tips.map((tip) => (
                  <li key={tip}>{tip}</li>
                ))}
              </ul>
            </article>

            <div className={styles.trendsPanel} id="trends">
              <div className={styles.trendHeader}>
                <h3>Trending looks</h3>
                <TrendingUp size={18} />
              </div>
              {trends.length ? (
                <div className={styles.trendList}>
                  {trends.map((trend) => (
                    <article key={trend.name} className={styles.trendCard}>
                      <strong>{trend.name}</strong>
                      <p>{trend.highlight}</p>
                      <span>{trend.source}</span>
                    </article>
                  ))}
                </div>
              ) : (
                <div className={styles.emptyState}>Trend-aware styling notes appear here after generation.</div>
              )}
            </div>

            {latest?.warnings?.length ? (
              <div className={styles.warningCard}>
                <CircleAlert size={16} />
                <p>{latest.warnings.join(" ")}</p>
              </div>
            ) : null}
          </aside>
        </section>
      </main>
    </div>
  );
}
