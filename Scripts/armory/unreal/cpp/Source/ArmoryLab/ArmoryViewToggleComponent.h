// ArmoryLab: first-person / third-person view toggle on V (user, 2026-10-01: "have the option to go to first person on
// the 'v' key"). Source of truth: Blender_Projects/Scripts/armory/unreal/cpp (make_project.py copies it into ArmoryLab).

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "InputCoreTypes.h"
#include "ArmoryViewToggleComponent.generated.h"

class ACharacter;
class UCameraComponent;
class UInputAction;
class UInputComponent;
class UInputMappingContext;

/**
 * Added to the ArmoryLab copy of BP_ThirdPersonCharacter by Scripts/armory/unreal/ak_firstperson.py.
 *
 * V (IA_ToggleView in IMC_ArmoryView, both under /Game/ArmoryLab/Input) switches between the template's own third-person
 * camera (CameraBoom + FollowCamera, untouched) and a first-person camera this component creates at the character's eyes.
 * In first person the body is hidden from its owner (it still casts its shadow), the character turns with the mouse
 * (controller yaw) instead of orienting to its movement, and mouse look is the template's (control rotation). V again
 * restores everything as it was.
 *
 * If no action / mapping context is assigned, a transient V mapping is made at runtime, so the toggle always works.
 * Self-test (game runs only): -AKViewToggleTest presses V through the player controller, walks in, looks round, presses V
 * again, logs "AK_VIEWTOGGLE ..." and quits (Scripts/armory/unreal/ak_fptest.ps1).
 */
UCLASS(ClassGroup=(Armory), meta=(BlueprintSpawnableComponent))
class ARMORYLAB_API UArmoryViewToggleComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UArmoryViewToggleComponent();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** The toggle action (IA_ToggleView). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Armory|View")
	TObjectPtr<UInputAction> ToggleViewAction;

	/** The mapping context that maps the toggle action to V (IMC_ArmoryView); added on top of the template's contexts. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Armory|View")
	TObjectPtr<UInputMappingContext> ToggleViewContext;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Armory|View")
	int32 ToggleViewContextPriority = 1;

	/** Key of the runtime fallback mapping (used only when no action or context is assigned). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Armory|View")
	FKey FallbackKey = EKeys::V;

	/** The skeleton bone the eye height is measured from (Manny / Quinn: "head"). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Armory|View")
	FName HeadBone = TEXT("head");

	/** Eyes relative to the head bone, in the character's frame (cm: forward, right, up). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Armory|View")
	FVector EyeOffset = FVector(12.0f, 0.0f, 8.0f);

	/** Horizontal field of view of the first-person camera. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Armory|View", meta=(ClampMin="40.0", ClampMax="120.0"))
	float FirstPersonFOV = 90.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Armory|View")
	bool bStartInFirstPerson = false;

	UFUNCTION(BlueprintCallable, Category="Armory|View")
	void ToggleView();

	UFUNCTION(BlueprintCallable, Category="Armory|View")
	void SetFirstPerson(bool bFirstPerson);

	UFUNCTION(BlueprintPure, Category="Armory|View")
	bool IsFirstPerson() const { return bIsFirstPerson; }

	/** Distance (cm) from the player's current view point to the head bone: about 3-4 m in third person, ~0.15 m in first. */
	UFUNCTION(BlueprintPure, Category="Armory|View")
	float GetViewDistanceFromHead() const;

private:
	ACharacter* GetCharacter() const;
	void EnsureFirstPersonCamera();
	void UpdateInputBinding();
	void OnTogglePressed();
	void TickSelfTest(float DeltaTime);
	void PressKeyForTest(bool bPressed);

	UPROPERTY(Transient)
	TObjectPtr<UCameraComponent> FirstPersonCamera;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> RuntimeAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> RuntimeContext;

	TWeakObjectPtr<UInputComponent> BoundInputComponent;
	bool bIsFirstPerson = false;
	int32 ToggleCount = 0;

	// what first person changes, restored on the way back
	TArray<TWeakObjectPtr<UCameraComponent>> ThirdPersonCameras;
	bool bSavedOrientToMovement = true;
	bool bSavedUseControllerYaw = false;
	bool bSavedCastHiddenShadow = false;

	// self-test state
	bool bSelfTest = false;
	int32 TestStage = 0;
	float TestClock = 0.0f;
	float TestStageClock = 0.0f;
	float TestThirdCm = -1.0f;
	float TestFirstCm = -1.0f;
	float TestBackCm = -1.0f;
	bool TestFirstFlag = false;
	bool TestBackFlag = true;
	FString TestKeys;
};
