export default function Question({ question, answer, onChange }) {
  return (
    <div className="question">
      <h2>{question.question}</h2>

      {Object.entries(question.options).map(([key, value]) => (
        <label key={key} className="option">
          <input
            type="radio"
            name="option"
            checked={answer === key}
            onChange={() => onChange(null, key)}
          />
          <span>{key}. {value}</span>
        </label>
      ))}
    </div>
  );
}
