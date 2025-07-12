import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function App() {
  return (
    <main className="min-h-screen bg-white text-gray-800 p-8 flex flex-col items-center justify-start">
      <div className="max-w-3xl text-center">
        <h1 className="text-4xl font-bold mb-4">📬 ColdCraft</h1>
        <p className="text-lg mb-6">
          Generate hyper-personalized cold email openers for every lead — powered by AI.
        </p>
        <div className="mb-8">
          <Button className="text-lg px-6 py-3">Try It Now</Button>
        </div>
        <Card className="mb-10">
          <CardContent className="p-6 space-y-4">
            <h2 className="text-2xl font-semibold">How It Works</h2>
            <ol className="list-decimal text-left pl-6">
              <li>Upload your lead list (CSV format)</li>
              <li>We generate 3 custom email openers per lead using AI</li>
              <li>Download the results — ready to A/B test</li>
            </ol>
          </CardContent>
        </Card>

        <div className="w-full max-w-md">
          <h3 className="text-xl font-semibold mb-2">Get Early Access</h3>
          <form action="https://formspree.io/f/your-form-id" method="POST" className="flex gap-2">
            <Input name="email" type="email" placeholder="you@example.com" required />
            <Button type="submit">Notify Me</Button>
          </form>
        </div>
      </div>
    </main>
  );
}
