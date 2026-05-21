import { Link } from "react-router-dom";

export const HomeButton = () => {
  return (
    <Link
      to="/"
      className="items-center bg-emerald-500 shadow-[rgba(255,102,0,0.3)_0px_4px_20px_0px] box-border caret-transparent gap-x-2 inline-flex text-[12.48px] font-bold justify-center tracking-[1.248px] leading-[19.968px] outline-[3px] relative gap-y-2 no-underline uppercase text-nowrap overflow-hidden px-[21.6px] py-[11.52px] rounded-[14px] font-montserrat md:px-7 md:py-[13.12px] hover:bg-emerald-600 hover:shadow-[rgba(255,102,0,0.45)_0px_8px_32px_0px]"
    >
      <svg
        className="w-4 h-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M10 19l-7-7m0 0l7-7m-7 7h18"
        />
      </svg>
      Go Home
    </Link>
  );
};