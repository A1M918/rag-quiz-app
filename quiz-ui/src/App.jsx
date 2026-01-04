import { useState } from "react";
import { startExam, submitExam } from "./api";
import Exam from "./components/Exam";
import Result from "./components/Result";
import "./styles.css";

export default function App() {
  const [level, setLevel] = useState("medium");
  const [exam, setExam] = useState(null);
  const [result, setResult] = useState(null);

  async function begin() {
    const data = await startExam(level);
    console.log("EXAM==>", data)

    setExam(data.exam);
    setResult(null);
  }

  async function finish(answers) {
    const res = await submitExam({
      exam,
      answers,
      level,
    });
    setResult(res);
    setLevel(res.next_level);
  }

  return (
    <div className="container">
      
      <h1>Spanish Traffic Theory Exam</h1>

      {!exam && !result && (
        <div className="exam-actions">
          <button onClick={begin}>Start Exam</button>
        </div>
      )}

      {exam && !result && (
        <Exam questions={exam} onSubmit={finish} />
      )}

      {result && (
        <Result result={result} onRestart={() => setExam(null)} />
      )}
      
    </div>
  );
}
