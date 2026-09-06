import MyPlanView from "../components/MyPlanView";

export default function WorkoutPlanPage() {
  return (
    <MyPlanView
      planType="workout"
      title="Workout plan"
      subtitle="Built by your coach from your profile and goals."
    />
  );
}
