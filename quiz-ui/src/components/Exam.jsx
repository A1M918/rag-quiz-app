import { useState } from "react";
import Question from "./Question";

export default function Exam({ questions, onSubmit }) {
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState(
    Array(questions.length).fill(null)
  );

  function setAnswer(value) {
    const copy = [...answers];
    copy[index] = value;
    setAnswers(copy);
  }

  const isLast = index === questions.length - 1;

  return (
    <div className="app-root">
    <div className="exam-card">
    {/* <div className="exam"> */}
      <div className="progress">
        Question {index + 1} / {questions.length}
      </div>

      <Question
        index={index}
        question={questions[index]}
        answer={answers[index]}
        onChange={(_, v) => setAnswer(v)}
      />

      <div className="navigation">
        <button
          disabled={index === 0}
          onClick={() => setIndex(index - 1)}
        >
          Previous
        </button>

        {!isLast ? (
          <button
            disabled={answers[index] === null}
            onClick={() => setIndex(index + 1)}
          >
            Next
          </button>
        ) : (
          <button
            disabled={answers.includes(null)}
            onClick={() => onSubmit(answers)}
          >
            Submit Exam
          </button>
        )}
      </div>
    {/* </div> */}
    </div>
    </div>
  );
}
