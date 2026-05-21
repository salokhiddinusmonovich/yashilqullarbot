import { useLang, Lang } from "../../../contexts/LanguageContext";

const LANGS: { code: Lang; label: string }[] = [
  // { code: "en", label: "EN" },
  // { code: "ru", label: "RU" },
  // { code: "uz", label: "UZ" },
];

export const LangSwitcher = () => {
  const { lang, setLang } = useLang();

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: "2px",
      background: "rgba(255,255,255,0.05)",
      border: "1px solid rgba(255,255,255,0.1)",
      borderRadius: "8px",
      padding: "3px",
    }}>
      {LANGS.map(({ code, label }) => (
        <button
          key={code}
          onClick={() => setLang(code)}
          style={{
            fontFamily: "'Montserrat', sans-serif",
            fontSize: "10px",
            fontWeight: 700,
            letterSpacing: "1px",
            padding: "5px 10px",
            borderRadius: "6px",
            border: "none",
            cursor: "pointer",
            transition: "background 0.2s, color 0.2s",
            background: lang === code ? "#10b981" : "transparent",
            color:      lang === code ? "#fff"     : "rgba(255,255,255,0.45)",
          }}
        >
          {label}
        </button>
      ))}
    </div>
  );
};
