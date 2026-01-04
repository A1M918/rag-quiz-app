export default function Result({ result, onRestart }) {
    // Handle backend error responses safely
    if (result.error) {
        return (
            <div>
                <h2>Submission Error</h2>
                <p>{result.error}</p>
                <button onClick={onRestart}>Start New Exam</button>
            </div>
        );
    }

    // Defensive fallback (should never happen, but safe)
    if (!result.details || !Array.isArray(result.details)) {
        return (
            <div>
                <h2>Unexpected Response</h2>
                <pre>{JSON.stringify(result, null, 2)}</pre>
                <button onClick={onRestart}>Start New Exam</button>
            </div>
        );
    }

    return (
        <div>
            <h2>Score: {result.score} / 30</h2>
            <h3>Next level: {result.next_level}</h3>

            <details>
                <summary>Review answers</summary>
                <hr />
                {result.details.map((d, i) => (
                    <div key={i} className={d.correct ? "correct" : "wrong"}>
                        <strong>Question {i + 1}</strong> —{" "}
                        {d.correct ? "Correct" : "Wrong"}
                        {!d.correct && d.explanation && (
                            <div className="boe">
                                <strong>Legal reference (BOE):</strong>
                                <p>{d.explanation}</p>
                            </div>
                        )}
                    </div>
                ))}
            </details>

            <button onClick={onRestart}>Start New Exam</button>
        </div>
    );
}
