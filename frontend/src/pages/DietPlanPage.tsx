import MyPlanView from "../components/MyPlanView";

export default function DietPlanPage() {
  return (
    <MyPlanView
      planType="diet"
      title="Diet plan"
      subtitle="Calorie and macro targets calculated from your metrics."
    />
  );
}
