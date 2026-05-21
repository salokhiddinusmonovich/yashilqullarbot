import { HomeButton } from "@/sections/NotFoundPage/components/HomeButton";

export const NotFoundPage = () => {
  return (
    <main className="box-border caret-transparent min-h-[1000px] outline-[3px] relative no-underline z-[1] pt-14 md:pt-16">
      <div className="items-center box-border caret-transparent flex flex-col justify-center min-h-[800px] outline-[3px] text-center no-underline p-8">
        <div className="box-border caret-transparent min-h-[auto] min-w-[auto] outline-[3px] no-underline">
          <div className="bg-clip-text bg-[linear-gradient(135deg,rgb(255,102,0),rgb(255,153,0))] box-border caret-transparent text-8xl font-black leading-[96px] outline-[3px] no-underline mb-6 font-montserrat md:text-[192px] md:leading-[192px]">
            404
          </div>
          <h1 className="box-border caret-transparent text-xl font-bold tracking-[-0.4px] leading-[21px] outline-[3px] no-underline mb-3 font-montserrat md:text-[32px] md:tracking-[-0.64px] md:leading-[33.6px]">
            Page not found
          </h1>
          <p className="box-border caret-transparent text-zinc-500 max-w-[400px] outline-[3px] no-underline mb-10">
            The page you are looking for does not exist or has been moved.
          </p>
          <HomeButton />
        </div>
      </div>
    </main>
  );
};